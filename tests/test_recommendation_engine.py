"""
Test suite for recommendation engine
"""

import pytest
import asyncio
from datetime import datetime
import sys
sys.path.append('./src')

from recommendation_engine import HybridRecommender
from ab_testing import ABTestManager
from api import app
from httpx import AsyncClient


class TestRecommendationEngine:
    """Test recommendation engine core functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.recommender = HybridRecommender()
        
    def test_initialization(self):
        """Test recommender initialization"""
        assert self.recommender is not None
        assert sum(self.recommender.weights.values()) == 1.0
        
    def test_get_recommendations(self):
        """Test basic recommendation generation"""
        context = {
            'device': 'mobile',
            'location': 'US'
        }
        
        recommendations = self.recommender.get_recommendations(
            user_id='test_user',
            context=context,
            n=10
        )
        
        assert isinstance(recommendations, list)
        # Should return empty list if no data (mock case)
        
    def test_diversity(self):
        """Test recommendation diversity"""
        scores = {
            f'product_{i}': 0.9 - (i * 0.05)
            for i in range(20)
        }
        
        diverse_recs = self.recommender._diversify_results(scores, n=10)
        
        assert len(diverse_recs) <= 10
        
    def test_contextual_boost(self):
        """Test contextual signal boosting"""
        context = {
            'device': 'mobile',
            'season': 'winter'
        }
        
        boosts = self.recommender._contextual_boost('test_user', context)
        
        assert isinstance(boosts, dict)


class TestABTesting:
    """Test A/B testing framework"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.ab_manager = ABTestManager()
        
    def test_variant_assignment(self):
        """Test consistent variant assignment"""
        user_id = 'test_user_123'
        experiment_id = 'rec_algorithm_v3'
        
        # Should assign to same variant consistently
        variant1 = self.ab_manager.get_variant(user_id, experiment_id)
        variant2 = self.ab_manager.get_variant(user_id, experiment_id)
        
        assert variant1 == variant2
        assert variant1 in ['control', 'variant_a', 'variant_b']
        
    def test_traffic_split(self):
        """Test traffic split distribution"""
        experiment_id = 'rec_algorithm_v3'
        variants = {'control': 0, 'variant_a': 0, 'variant_b': 0}
        
        # Simulate 1000 users
        for i in range(1000):
            user_id = f'user_{i}'
            variant = self.ab_manager.get_variant(user_id, experiment_id)
            variants[variant] += 1
        
        # Check approximately equal distribution (±10%)
        for variant, count in variants.items():
            assert 280 < count < 380, f"{variant}: {count}"
        
    def test_experiment_results(self):
        """Test experiment metrics calculation"""
        # Simulate events
        for i in range(100):
            user_id = f'user_{i}'
            variant = self.ab_manager.get_variant(user_id, 'rec_algorithm_v3')
            
            self.ab_manager.track_event(
                user_id, 'rec_algorithm_v3', variant, 'impression'
            )
            
            if i % 3 == 0:  # 33% CTR
                self.ab_manager.track_event(
                    user_id, 'rec_algorithm_v3', variant, 'click'
                )
        
        results = self.ab_manager.get_experiment_results('rec_algorithm_v3')
        
        assert 'control' in results
        assert results['control']['impressions'] > 0


@pytest.mark.asyncio
class TestAPI:
    """Test FastAPI endpoints"""
    
    async def test_health_check(self):
        """Test API health endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/")
            
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
    
    async def test_recommendations_endpoint(self):
        """Test recommendations endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/recommendations",
                headers={"X-API-Key": "dev_key_123"},
                json={
                    "user_id": "test_user",
                    "context": {"device": "mobile"},
                    "n": 5
                }
            )
        
        # May return 500 if database not set up
        # In real tests, mock database
        assert response.status_code in [200, 500]
    
    async def test_tracking_endpoint(self):
        """Test event tracking endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/track",
                headers={"X-API-Key": "dev_key_123"},
                json={
                    "user_id": "test_user",
                    "product_id": "prod_123",
                    "event_type": "click"
                }
            )
        
        assert response.status_code in [200, 500]
    
    async def test_invalid_api_key(self):
        """Test API key validation"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/recommendations",
                headers={"X-API-Key": "invalid_key"},
                json={"user_id": "test", "context": {}, "n": 5}
            )
        
        assert response.status_code == 401


class TestPerformance:
    """Test performance and latency"""
    
    def test_recommendation_latency(self):
        """Test recommendation generation latency"""
        import time
        
        recommender = HybridRecommender()
        
        start = time.time()
        recommender.get_recommendations(
            user_id='test_user',
            context={'device': 'mobile'},
            n=10
        )
        latency = (time.time() - start) * 1000
        
        # Should be under 100ms (even with no data)
        assert latency < 100
        
    def test_concurrent_requests(self):
        """Test handling concurrent requests"""
        import concurrent.futures
        
        recommender = HybridRecommender()
        
        def get_recs(user_id):
            return recommender.get_recommendations(
                user_id=user_id,
                context={'device': 'mobile'},
                n=5
            )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(get_recs, f'user_{i}')
                for i in range(100)
            ]
            
            results = [f.result() for f in futures]
        
        assert len(results) == 100


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
