# API Documentation

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
All API endpoints require an API key passed in the `X-API-Key` header.

```bash
curl -H "X-API-Key: your_api_key" http://localhost:8000/api/v1/recommendations
```

---

## Endpoints

### 1. Get Recommendations

**POST** `/recommendations`

Generate personalized product recommendations for a user.

#### Request Body
```json
{
  "user_id": "string",
  "session_id": "string (optional)",
  "context": {
    "device": "mobile|desktop",
    "location": "string (optional)",
    "page_type": "string (optional)",
    "referrer": "string (optional)"
  },
  "n": 10,
  "exclude_products": ["product_id1", "product_id2"]
}
```

#### Response
```json
{
  "recommendations": [
    {
      "product_id": "string",
      "name": "string",
      "price": 99.99,
      "image_url": "string",
      "category": "string",
      "url": "string",
      "confidence_score": 0.85,
      "reason": "string"
    }
  ],
  "algorithm_version": "string",
  "latency_ms": 45.2,
  "experiment_id": "string",
  "variant": "string",
  "total_count": 10
}
```

#### Example
```bash
curl -X POST "http://localhost:8000/api/v1/recommendations" \
  -H "X-API-Key: dev_key_123" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "context": {
      "device": "mobile",
      "location": "US"
    },
    "n": 5
  }'
```

---

### 2. Track Event

**POST** `/track`

Track user interaction events (views, clicks, purchases).

#### Request Body
```json
{
  "user_id": "string",
  "product_id": "string",
  "event_type": "view|click|add_to_cart|purchase",
  "session_id": "string (optional)",
  "metadata": {
    "order_value": 99.99,
    "source": "string"
  }
}
```

#### Response
```json
{
  "status": "success",
  "event_id": "string"
}
```

#### Example
```bash
curl -X POST "http://localhost:8000/api/v1/track" \
  -H "X-API-Key: dev_key_123" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "product_id": "prod_456",
    "event_type": "purchase",
    "metadata": {
      "order_value": 79.99
    }
  }'
```

---

### 3. Get Trending Products

**GET** `/trending`

Retrieve currently trending products.

#### Query Parameters
- `n`: Number of products (default: 20, max: 50)
- `category`: Filter by category (optional)

#### Response
```json
{
  "trending_products": [
    {
      "product_id": "string",
      "name": "string",
      "price": 99.99,
      "image_url": "string",
      "category": "string",
      "url": "string",
      "confidence_score": 0.95,
      "reason": "Trending now"
    }
  ],
  "count": 20,
  "category": "Electronics"
}
```

#### Example
```bash
curl -X GET "http://localhost:8000/api/v1/trending?n=10&category=Electronics" \
  -H "X-API-Key: dev_key_123"
```

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Invalid API key"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error message"
}
```

---

## Rate Limiting

- Rate limit: 100 requests per minute per API key
- Burst limit: 10 requests per second

---

## Best Practices

1. **Cache recommendations** on the client side for 5-10 minutes
2. **Track all events** (impressions, clicks, purchases) for better personalization
3. **Use context signals** (device, location, time) for more relevant recommendations
4. **Exclude current product** when showing related items
5. **A/B test** different recommendation strategies

---

## SDKs

### JavaScript
```javascript
import RecEngine from 'rec-engine-sdk';

RecEngine.init({
  apiKey: 'your_api_key',
  apiUrl: 'http://localhost:8000'
});

const recs = await RecEngine.getRecommendations({
  userId: 'user_123',
  context: { device: 'mobile' },
  n: 8
});
```

### Python
```python
from rec_engine_client import RecEngineClient

client = RecEngineClient(
    api_key='your_api_key',
    api_url='http://localhost:8000'
)

recs = client.get_recommendations(
    user_id='user_123',
    context={'device': 'mobile'},
    n=8
)
```
