"""
E-Commerce Recommendation Engine - Core Implementation
Hybrid approach: Collaborative Filtering + Content-Based + Contextual + Trending
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import redis
import json
import pickle
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HybridRecommender:
    def __init__(self, 
                 cf_weight=0.4, 
                 cb_weight=0.3, 
                 context_weight=0.2, 
                 trending_weight=0.1,
                 redis_host='localhost',
                 redis_port=6379):
        """
        Initialize hybrid recommendation engine
        
        Args:
            cf_weight: Collaborative filtering weight
            cb_weight: Content-based filtering weight
            context_weight: Contextual signal weight
            trending_weight: Trending items weight
        """
        self.weights = {
            'collaborative': cf_weight,
            'content_based': cb_weight,
            'contextual': context_weight,
            'trending': trending_weight
        }
        
        try:
            self.redis_client = redis.Redis(
                host=redis_host, 
                port=redis_port,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("Redis connection established")
        except redis.ConnectionError:
            logger.warning("Redis connection failed. Using in-memory cache.")
            self.redis_client = None
            self._cache = {}
        
        # Load pre-trained models
        self.user_vectors = {}
        self.product_vectors = {}
        self.user_product_matrix = None
        
    def get_recommendations(self, 
                          user_id: str, 
                          context: Dict, 
                          n: int = 10,
                          exclude_products: List[str] = None) -> List[Tuple[str, float]]:
        """
        Generate top-N recommendations with <100ms latency
        
        Args:
            user_id: User identifier
            context: Contextual information (device, location, time, etc.)
            n: Number of recommendations to return
            exclude_products: Products to exclude from recommendations
            
        Returns:
            List of (product_id, score) tuples
        """
        exclude_products = exclude_products or []
        scores = defaultdict(float)
        
        # Parallel score computation
        try:
            # 1. Collaborative Filtering
            cf_scores = self._collaborative_filter(user_id)
            
            # 2. Content-Based Filtering
            cb_scores = self._content_based_filter(user_id)
            
            # 3. Contextual Signals
            ctx_scores = self._contextual_boost(user_id, context)
            
            # 4. Trending Items
            trend_scores = self._trending_items(context)
            
            # Weighted ensemble
            all_products = set(cf_scores.keys()) | set(cb_scores.keys()) | \
                          set(ctx_scores.keys()) | set(trend_scores.keys())
            
            for product_id in all_products:
                if product_id in exclude_products:
                    continue
                    
                scores[product_id] = (
                    self.weights['collaborative'] * cf_scores.get(product_id, 0) +
                    self.weights['content_based'] * cb_scores.get(product_id, 0) +
                    self.weights['contextual'] * ctx_scores.get(product_id, 0) +
                    self.weights['trending'] * trend_scores.get(product_id, 0)
                )
            
            # Diversity re-ranking (MMR approach)
            recommendations = self._diversify_results(scores, n)
            
            logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            # Fallback to trending items
            return self._fallback_recommendations(context, n)
    
    def _collaborative_filter(self, user_id: str) -> Dict[str, float]:
        """
        Collaborative filtering using matrix factorization
        Uses Redis cache for performance
        """
        cache_key = f"cf:{user_id}"
        
        # Check cache
        if self.redis_client:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        elif hasattr(self, '_cache') and cache_key in self._cache:
            return self._cache[cache_key]
        
        # Compute CF scores
        scores = self._compute_cf_scores(user_id)
        
        # Cache results (5 min TTL)
        if self.redis_client:
            self.redis_client.setex(cache_key, 300, json.dumps(scores))
        else:
            self._cache[cache_key] = scores
        
        return scores
    
    def _compute_cf_scores(self, user_id: str) -> Dict[str, float]:
        """
        Compute collaborative filtering scores using ALS/SVD
        In production, use pre-trained models from Apache Spark MLlib or Surprise
        """
        scores = {}
        
        # Placeholder: Load user vector and compute dot product with item vectors
        if user_id in self.user_vectors:
            user_vec = self.user_vectors[user_id]
            
            for product_id, product_vec in self.product_vectors.items():
                score = np.dot(user_vec, product_vec)
                scores[product_id] = float(score)
        else:
            # Cold start: Use popular items
            logger.warning(f"User {user_id} not found in CF model")
        
        return scores
    
    def _content_based_filter(self, user_id: str) -> Dict[str, float]:
        """
        Content-based filtering using product attributes
        Computes similarity between user profile and product features
        """
        user_profile = self._get_user_profile(user_id)
        if not user_profile:
            return {}
        
        scores = {}
        for product_id, product_vec in self.product_vectors.items():
            similarity = cosine_similarity([user_profile], [product_vec])[0][0]
            scores[product_id] = float(similarity)
        
        return scores
    
    def _get_user_profile(self, user_id: str) -> Optional[np.ndarray]:
        """
        Build user profile from interaction history
        Average of interacted product vectors
        """
        # Placeholder: Query user interaction history
        interacted_products = self._get_user_interactions(user_id)
        
        if not interacted_products:
            return None
        
        vectors = [self.product_vectors[pid] for pid in interacted_products 
                  if pid in self.product_vectors]
        
        if not vectors:
            return None
        
        return np.mean(vectors, axis=0)
    
    def _get_user_interactions(self, user_id: str) -> List[str]:
        """
        Fetch user interaction history (views, purchases, cart)
        """
        # Placeholder: Query from database
        # In production, query PostgreSQL/MongoDB
        return []
    
    def _contextual_boost(self, user_id: str, context: Dict) -> Dict[str, float]:
        """
        Apply contextual boosts based on:
        - Time (seasonal products)
        - Location (regional availability)
        - Device (mobile-friendly products)
        - Referral source
        """
        boosts = defaultdict(float)
        
        # Seasonal products
        season = context.get('season', self._get_current_season())
        seasonal_products = self._get_seasonal_products(season)
        for pid in seasonal_products:
            boosts[pid] += 0.3
        
        # Device-specific (mobile = smaller/portable items)
        if context.get('device') == 'mobile':
            mobile_products = self._get_mobile_friendly_products()
            for pid in mobile_products:
                boosts[pid] += 0.2
        
        # Location-based inventory
        location = context.get('location')
        if location:
            local_products = self._get_local_inventory(location)
            for pid in local_products:
                boosts[pid] += 0.25
        
        # Time-of-day patterns
        hour = context.get('hour', 12)
        time_products = self._get_time_based_products(hour)
        for pid in time_products:
            boosts[pid] += 0.15
        
        return dict(boosts)
    
    def _trending_items(self, context: Dict) -> Dict[str, float]:
        """
        Get real-time trending products
        Uses Redis sorted sets for efficient ranking
        """
        if not self.redis_client:
            return {}
        
        try:
            # Get top 100 trending items from last 24h
            trending = self.redis_client.zrevrange(
                'trending:24h', 0, 99, withscores=True
            )
            
            # Normalize scores to 0-1 range
            if trending:
                max_score = max(score for _, score in trending)
                return {
                    str(pid): float(score) / max_score 
                    for pid, score in trending
                }
        except Exception as e:
            logger.error(f"Error fetching trending items: {str(e)}")
        
        return {}
    
    def _diversify_results(self, scores: Dict[str, float], n: int) -> List[Tuple[str, float]]:
        """
        Apply Maximal Marginal Relevance (MMR) for diversity
        Balances relevance and diversity to avoid filter bubbles
        """
        if not scores:
            return []
        
        selected = []
        candidates = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # MMR parameter: higher = more relevance, lower = more diversity
        lambda_param = 0.7
        
        while len(selected) < n and candidates:
            if not selected:
                # First item: highest score
                selected.append(candidates.pop(0))
                continue
            
            mmr_scores = []
            for prod_id, rel_score in candidates:
                # Maximum similarity to already selected items
                max_sim = max([
                    self._product_similarity(prod_id, s[0]) 
                    for s in selected
                ])
                
                # MMR formula: λ * Relevance - (1-λ) * MaxSimilarity
                mmr = lambda_param * rel_score - (1 - lambda_param) * max_sim
                mmr_scores.append((prod_id, rel_score, mmr))
            
            # Pick item with highest MMR score
            best = max(mmr_scores, key=lambda x: x[2])
            selected.append((best[0], best[1]))
            
            # Remove selected item from candidates
            candidates = [(p, s) for p, s, _ in mmr_scores if p != best[0]]
        
        return selected
    
    def _product_similarity(self, prod_id1: str, prod_id2: str) -> float:
        """
        Compute similarity between two products
        """
        if prod_id1 not in self.product_vectors or prod_id2 not in self.product_vectors:
            return 0.0
        
        vec1 = self.product_vectors[prod_id1]
        vec2 = self.product_vectors[prod_id2]
        
        similarity = cosine_similarity([vec1], [vec2])[0][0]
        return float(similarity)
    
    def _fallback_recommendations(self, context: Dict, n: int) -> List[Tuple[str, float]]:
        """
        Fallback strategy when main algorithm fails
        Returns trending or bestseller items
        """
        logger.warning("Using fallback recommendations")
        trending = self._trending_items(context)
        
        if trending:
            sorted_trending = sorted(trending.items(), key=lambda x: x[1], reverse=True)
            return sorted_trending[:n]
        
        # Ultimate fallback: random popular items
        return []
    
    def _get_current_season(self) -> str:
        """Get current season based on month"""
        from datetime import datetime
        month = datetime.now().month
        
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'fall'
    
    def _get_seasonal_products(self, season: str) -> List[str]:
        """Fetch seasonal product catalog"""
        # Placeholder: Query product database
        return []
    
    def _get_mobile_friendly_products(self) -> List[str]:
        """Get products optimized for mobile shopping"""
        # Placeholder: Query product attributes
        return []
    
    def _get_local_inventory(self, location: str) -> List[str]:
        """Get products available in user's region"""
        # Placeholder: Query inventory database
        return []
    
    def _get_time_based_products(self, hour: int) -> List[str]:
        """Get products relevant to time of day"""
        # Morning: coffee, breakfast items
        # Evening: dinner, entertainment
        return []
    
    def update_trending(self, product_id: str, score_increment: float = 1.0):
        """
        Update trending scores in real-time
        Called on product views, purchases
        """
        if self.redis_client:
            self.redis_client.zincrby('trending:24h', score_increment, product_id)
    
    def load_models(self, model_path: str):
        """
        Load pre-trained models (user vectors, product vectors, etc.)
        """
        try:
            with open(f"{model_path}/user_vectors.pkl", 'rb') as f:
                self.user_vectors = pickle.load(f)
            
            with open(f"{model_path}/product_vectors.pkl", 'rb') as f:
                self.product_vectors = pickle.load(f)
            
            logger.info(f"Loaded models from {model_path}")
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
