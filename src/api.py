"""
FastAPI REST API for Recommendation Engine
Provides real-time recommendations with <100ms latency
"""

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import time
import asyncio
from datetime import datetime
import logging

from recommendation_engine import HybridRecommender
from ab_testing import ABTestManager
from database import get_db, get_user_data, get_product_details

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="E-Commerce Recommendation API",
    description="AI-powered product recommendations",
    version="2.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize recommendation engine
recommender = HybridRecommender()
ab_manager = ABTestManager()

# Load pre-trained models
try:
    recommender.load_models("./models")
except Exception as e:
    logger.warning(f"Could not load models: {e}")


# Request/Response Models
class RecommendationRequest(BaseModel):
    user_id: str = Field(..., description="User identifier (use 'anonymous' for new users)")
    session_id: Optional[str] = Field(None, description="Session identifier for anonymous users")
    context: Dict = Field(
        default_factory=dict,
        description="Context: device, location, page_type, referrer, etc.",
        example={
            "device": "mobile",
            "location": "US",
            "page_type": "product_detail",
            "referrer": "google"
        }
    )
    n: int = Field(10, ge=1, le=50, description="Number of recommendations")
    exclude_products: Optional[List[str]] = Field(
        default_factory=list,
        description="Product IDs to exclude"
    )


class Product(BaseModel):
    product_id: str
    name: str
    price: float
    image_url: str
    category: str
    url: str
    confidence_score: float
    reason: str  # Why this was recommended


class RecommendationResponse(BaseModel):
    recommendations: List[Product]
    algorithm_version: str
    latency_ms: float
    experiment_id: Optional[str] = None
    variant: Optional[str] = None
    total_count: int


class TrackingEvent(BaseModel):
    user_id: str
    product_id: str
    event_type: str  # 'view', 'click', 'add_to_cart', 'purchase'
    session_id: Optional[str] = None
    metadata: Optional[Dict] = Field(default_factory=dict)


# API Key validation (simple example)
async def verify_api_key(x_api_key: str = Header(...)):
    """Validate API key from header"""
    valid_keys = ["dev_key_123", "prod_key_456"]  # Load from config
    
    if x_api_key not in valid_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return x_api_key


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "recommendation-engine",
        "version": "2.1.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Generate personalized product recommendations
    
    - **user_id**: User identifier or 'anonymous'
    - **context**: Contextual signals (device, location, etc.)
    - **n**: Number of recommendations (1-50)
    - **exclude_products**: Products to exclude from results
    """
    start_time = time.time()
    
    try:
        # Get A/B test variant
        experiment_id = "rec_algorithm_v3"
        variant = ab_manager.get_variant(request.user_id, experiment_id)
        variant_config = ab_manager.experiments[experiment_id].variants[variant]
        
        # Initialize recommender with variant config
        variant_recommender = HybridRecommender(**variant_config)
        
        # Handle cold-start (new users)
        if request.user_id == "anonymous" or not await user_exists(request.user_id):
            recommendations = await get_cold_start_recommendations(request)
        else:
            # Get recommendations
            rec_scores = variant_recommender.get_recommendations(
                user_id=request.user_id,
                context=request.context,
                n=request.n,
                exclude_products=request.exclude_products
            )
            
            # Enrich with product details
            recommendations = await enrich_products(rec_scores, request.context)
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Track impression event
        await track_impressions(
            request.user_id,
            [r.product_id for r in recommendations],
            experiment_id,
            variant
        )
        
        logger.info(
            f"Recommendations generated: user={request.user_id}, "
            f"count={len(recommendations)}, latency={latency_ms:.2f}ms, "
            f"variant={variant}"
        )
        
        return RecommendationResponse(
            recommendations=recommendations,
            algorithm_version="hybrid_v2.1",
            latency_ms=latency_ms,
            experiment_id=experiment_id,
            variant=variant,
            total_count=len(recommendations)
        )
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/track")
async def track_event(
    event: TrackingEvent,
    api_key: str = Depends(verify_api_key)
):
    """
    Track user interaction events
    
    - **event_type**: 'view', 'click', 'add_to_cart', 'purchase'
    - **product_id**: Product that was interacted with
    """
    try:
        # Update trending scores
        if event.event_type in ['view', 'click']:
            recommender.update_trending(event.product_id, score_increment=1.0)
        elif event.event_type == 'purchase':
            recommender.update_trending(event.product_id, score_increment=5.0)
        
        # Track in analytics database
        await store_event(event)
        
        # Track A/B test conversion
        if 'experiment_id' in event.metadata:
            ab_manager.track_event(
                user_id=event.user_id,
                experiment_id=event.metadata['experiment_id'],
                variant=event.metadata.get('variant', 'control'),
                event_type=event.event_type,
                metadata=event.metadata
            )
        
        return {"status": "success", "event_id": generate_event_id()}
        
    except Exception as e:
        logger.error(f"Error tracking event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/trending")
async def get_trending_products(
    n: int = 20,
    category: Optional[str] = None,
    api_key: str = Depends(verify_api_key)
):
    """
    Get currently trending products
    """
    try:
        context = {"category": category} if category else {}
        trending_scores = recommender._trending_items(context)
        
        # Get top N
        top_trending = sorted(
            trending_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n]
        
        # Enrich with product details
        products = await enrich_products(top_trending, {})
        
        return {
            "trending_products": products,
            "count": len(products),
            "category": category
        }
        
    except Exception as e:
        logger.error(f"Error fetching trending: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
async def user_exists(user_id: str) -> bool:
    """Check if user exists in database"""
    # Placeholder: Query user database
    return True


async def get_cold_start_recommendations(request: RecommendationRequest) -> List[Product]:
    """
    Handle recommendations for new users
    Strategy: trending + category bestsellers + personalized defaults
    """
    strategies = await asyncio.gather(
        get_trending_products_internal(request.context, n=5),
        get_category_bestsellers(request.context, n=3),
        get_personalized_default(request.session_id, n=2)
    )
    
    # Combine and deduplicate
    all_products = []
    seen_ids = set()
    
    for strategy_products in strategies:
        for product in strategy_products:
            if product.product_id not in seen_ids:
                all_products.append(product)
                seen_ids.add(product.product_id)
    
    return all_products[:request.n]


async def get_trending_products_internal(context: Dict, n: int) -> List[Product]:
    """Get trending products"""
    trending_scores = recommender._trending_items(context)
    top_items = sorted(trending_scores.items(), key=lambda x: x[1], reverse=True)[:n]
    return await enrich_products(top_items, context)


async def get_category_bestsellers(context: Dict, n: int) -> List[Product]:
    """Get bestsellers in inferred category"""
    # Placeholder: Infer category from context and get bestsellers
    return []


async def get_personalized_default(session_id: Optional[str], n: int) -> List[Product]:
    """Get personalized defaults based on session behavior"""
    # Placeholder: Analyze session activity
    return []


async def enrich_products(
    product_scores: List[tuple],
    context: Dict
) -> List[Product]:
    """
    Enrich product IDs with full details
    """
    enriched = []
    
    for product_id, score in product_scores:
        # Fetch product details from database
        details = await get_product_details(product_id)
        
        if details:
            enriched.append(Product(
                product_id=product_id,
                name=details.get('name', 'Unknown Product'),
                price=details.get('price', 0.0),
                image_url=details.get('image_url', ''),
                category=details.get('category', 'Other'),
                url=details.get('url', f'/products/{product_id}'),
                confidence_score=round(score, 3),
                reason=generate_reason(score, context)
            ))
    
    return enriched


def generate_reason(score: float, context: Dict) -> str:
    """Generate human-readable recommendation reason"""
    if score > 0.8:
        return "Highly recommended for you"
    elif score > 0.6:
        return "Customers like you also bought this"
    elif score > 0.4:
        return "Trending now"
    else:
        return "You might also like"


async def track_impressions(
    user_id: str,
    product_ids: List[str],
    experiment_id: str,
    variant: str
):
    """Track recommendation impressions"""
    # Placeholder: Store in analytics database
    pass


async def store_event(event: TrackingEvent):
    """Store tracking event in database"""
    # Placeholder: Insert into analytics database
    pass


def generate_event_id() -> str:
    """Generate unique event ID"""
    import uuid
    return str(uuid.uuid4())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
