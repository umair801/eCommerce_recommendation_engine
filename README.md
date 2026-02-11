# E-Commerce AI Recommendation Engine

Production-ready recommendation system with hybrid algorithms, real-time personalization, A/B testing, and comprehensive analytics.

## Features

- **Hybrid Recommendation Algorithm**: Combines collaborative filtering, content-based, contextual signals, and trending items
- **Real-time Performance**: <100ms API latency
- **Cold Start Handling**: Multiple fallback strategies for new users
- **A/B Testing Framework**: Built-in experiment management and statistical analysis
- **Email Campaigns**: Automated personalized product recommendations
- **Analytics Dashboard**: Real-time performance monitoring with Streamlit
- **Scalable Architecture**: Redis caching, PostgreSQL storage, Docker deployment

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Website   │────▶│  FastAPI API │────▶│ Recommender │
│  Mobile App │     │              │     │   Engine    │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                     │
                           ▼                     ▼
                    ┌──────────┐          ┌──────────┐
                    │  Redis   │          │PostgreSQL│
                    │  Cache   │          │ Database │
                    └──────────┘          └──────────┘
```

## Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### 2. Installation

Clone the repository:
```bash
git clone <repository-url>
cd ecommerce_recommendation_engine
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Database Setup

Create database tables:
```bash
python src/database.py
```

### 4. Start Services

**Option A: Docker (Recommended)**
```bash
docker-compose up -d
```

**Option B: Manual**
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start PostgreSQL
# (Ensure PostgreSQL is running)

# Terminal 3: Start API
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload

# Terminal 4: Start Dashboard
streamlit run src/dashboard.py --server.port 8501
```

### 5. Access Services

- **API Documentation**: http://localhost:8000/docs
- **Analytics Dashboard**: http://localhost:8501
- **API Health Check**: http://localhost:8000/

## API Usage

### Get Recommendations

```bash
curl -X POST "http://localhost:8000/api/v1/recommendations" \
  -H "X-API-Key: dev_key_123" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "context": {
      "device": "mobile",
      "location": "US",
      "page_type": "homepage"
    },
    "n": 10
  }'
```

Response:
```json
{
  "recommendations": [
    {
      "product_id": "prod_456",
      "name": "Wireless Headphones",
      "price": 79.99,
      "image_url": "https://...",
      "category": "Electronics",
      "url": "/products/prod_456",
      "confidence_score": 0.89,
      "reason": "Customers like you also bought this"
    }
  ],
  "algorithm_version": "hybrid_v2.1",
  "latency_ms": 45.2,
  "experiment_id": "rec_algorithm_v3",
  "variant": "variant_a",
  "total_count": 10
}
```

### Track Events

```bash
curl -X POST "http://localhost:8000/api/v1/track" \
  -H "X-API-Key: dev_key_123" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "product_id": "prod_456",
    "event_type": "click",
    "metadata": {
      "source": "email",
      "campaign": "weekly_digest"
    }
  }'
```

## Integration Examples

### JavaScript/React

```javascript
// Initialize recommendation widget
import RecEngine from './rec-engine-sdk';

RecEngine.init({
  apiKey: 'your_api_key',
  apiUrl: 'http://localhost:8000',
  userId: getCurrentUserId(),
  context: {
    device: isMobile() ? 'mobile' : 'desktop',
    location: getUserLocation()
  }
});

// Get recommendations
const recs = await RecEngine.getRecommendations({
  n: 8,
  excludeProducts: getCurrentProductId()
});

// Track click
RecEngine.trackClick(productId);
```

### Shopify Integration

```liquid
<!-- Add to theme.liquid -->
<div id="recommendations"></div>

<script src="https://cdn.yoursite.com/rec-widget.js"></script>
<script>
  RecEngine.init({
    apiKey: '{{ settings.rec_api_key }}',
    userId: '{{ customer.id | default: "anonymous" }}',
    context: {
      device: '{{ request.user_agent | device_type }}',
      page: '{{ template }}'
    }
  });
  
  RecEngine.render('#recommendations', {
    title: 'You Might Also Like',
    layout: 'carousel'
  });
</script>
```

## Email Campaigns

Send personalized email recommendations:

```python
from email_recommendations import EmailRecommender
import asyncio

async def send_weekly_digest():
    recommender = EmailRecommender()
    
    user_ids = get_active_users()  # Your user query
    
    for user_id in user_ids:
        await recommender.send_personalized_email(
            user_id=user_id,
            email_type='weekly_digest'
        )

asyncio.run(send_weekly_digest())
```

Campaign types:
- `browse_abandonment`: Users who viewed but didn't purchase
- `cart_abandonment`: Users with items in cart
- `post_purchase`: Complementary products after purchase
- `weekly_digest`: Regular personalized updates
- `price_drop`: Alert for price drops on viewed items
- `back_in_stock`: Notify when wishlist items return
- `win_back`: Re-engage inactive users

## A/B Testing

### Create Experiment

```python
from ab_testing import ABTestManager

manager = ABTestManager()

experiment = manager.create_experiment(
    experiment_id='new_algorithm',
    name='Testing New Weight Distribution',
    variants={
        'control': {'cf_weight': 0.4, 'cb_weight': 0.3},
        'variant_a': {'cf_weight': 0.6, 'cb_weight': 0.2}
    },
    traffic_split={'control': 0.5, 'variant_a': 0.5}
)

manager.activate_experiment('new_algorithm')
```

### View Results

Access the analytics dashboard at http://localhost:8501 or:

```python
results = manager.get_experiment_results('new_algorithm')
significance = manager.calculate_statistical_significance('new_algorithm')

print(results)
print(significance)
```

## Configuration

### Algorithm Weights

Adjust in `src/recommendation_engine.py`:

```python
recommender = HybridRecommender(
    cf_weight=0.4,         # Collaborative filtering
    cb_weight=0.3,         # Content-based
    context_weight=0.2,    # Contextual signals
    trending_weight=0.1    # Trending items
)
```

### Diversity Settings

Control recommendation diversity (MMR lambda):

```python
# In _diversify_results method
lambda_param = 0.7  # Higher = more relevance, Lower = more diversity
```

## Performance Optimization

### Redis Caching

- Collaborative filtering results cached for 5 minutes
- Trending items updated in real-time
- User profiles cached per session

### Database Indexes

Key indexes created automatically:
- `user_interactions(user_id, timestamp)`
- `recommendation_events(experiment_id, variant)`
- `products(category)`

### API Optimization

- Async I/O for database queries
- Parallel score computation
- Response caching for anonymous users

## Monitoring & Analytics

### Key Metrics

The dashboard tracks:
- **CTR (Click-Through Rate)**: % of impressions that generate clicks
- **Conversion Rate**: % of clicks that lead to purchases
- **Revenue Attribution**: Revenue generated from recommendations
- **Average Order Value**: Average purchase value
- **Diversity Scores**: Category and product diversity

### Target Benchmarks

| Metric | Baseline | Target | Excellent |
|--------|----------|--------|-----------|
| CTR | 1-2% | 3-4% | 5%+ |
| Conversion | 15-20% | 25-30% | 35%+ |
| Revenue Lift | - | +20-40% | +50%+ |
| Latency | - | <100ms | <50ms |

## Deployment

### Production Checklist

- [ ] Set strong API keys in `.env`
- [ ] Configure production database credentials
- [ ] Enable HTTPS for API endpoints
- [ ] Set up monitoring (Datadog, New Relic)
- [ ] Configure CORS for your domains
- [ ] Set up automated backups
- [ ] Enable rate limiting
- [ ] Configure email service (SendGrid, AWS SES)

### Scaling Recommendations

**Horizontal Scaling**:
```bash
# Scale API instances
docker-compose up --scale api=3
```

**Vertical Scaling**:
- Increase Redis memory for larger caches
- Use PostgreSQL read replicas
- Pre-compute recommendations offline

**Model Training**:
- Train CF models offline (Apache Spark MLlib)
- Update product vectors nightly
- Retrain weekly with new data

## Troubleshooting

### Common Issues

**Redis connection failed**:
```bash
# Check Redis is running
redis-cli ping

# Should return: PONG
```

**Database connection error**:
```bash
# Test PostgreSQL connection
psql -h localhost -U postgres -d ecommerce
```

**Slow API responses**:
- Check Redis cache hit rate
- Review database query performance
- Monitor API logs for bottlenecks

## Testing

Run tests:
```bash
pytest tests/ -v
```

Load testing:
```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load_test.py --host=http://localhost:8000
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: [repository-url]/issues
- Documentation: [docs-url]
- Email: support@yourcompany.com

## Roadmap

- [ ] Deep learning models (neural collaborative filtering)
- [ ] Real-time feature engineering
- [ ] Multi-armed bandit algorithms
- [ ] Graph-based recommendations
- [ ] Session-based recommendations (RNN/Transformer)
- [ ] Explainable AI features
- [ ] Mobile SDK (iOS/Android)
- [ ] Recommendation diversity optimization
