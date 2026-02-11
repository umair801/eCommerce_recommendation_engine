# Quick Start Guide

Get the recommendation engine running in 5 minutes!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set your database credentials.

## Step 3: Start with Docker (Easiest)

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database
- Redis cache
- API server (port 8000)
- Analytics dashboard (port 8501)

## Step 4: Setup Database

```bash
python src/database.py
```

## Step 5: Generate Sample Data

```bash
python scripts/generate_data.py
```

## Step 6: Test the API

```bash
curl -X POST "http://localhost:8000/api/v1/recommendations" \
  -H "X-API-Key: dev_key_123" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_000001",
    "context": {"device": "mobile"},
    "n": 5
  }'
```

## Step 7: View Dashboard

Open http://localhost:8501 in your browser to see analytics.

---

## Alternative: Manual Setup

If you don't use Docker:

1. Start Redis:
```bash
redis-server
```

2. Start PostgreSQL (ensure it's running)

3. Start API:
```bash
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

4. Start Dashboard (new terminal):
```bash
streamlit run src/dashboard.py
```

---

## Next Steps

1. **Integrate with your website**: See `templates/shopify_integration.js`
2. **Configure email campaigns**: Edit `src/email_recommendations.py`
3. **Run A/B tests**: Use `src/ab_testing.py`
4. **Monitor performance**: Check dashboard at http://localhost:8501

---

## Troubleshooting

**Redis connection error?**
```bash
redis-cli ping  # Should return PONG
```

**Database error?**
```bash
psql -h localhost -U postgres -d ecommerce
```

**Port already in use?**
Edit `docker-compose.yml` to change ports.

---

## Production Deployment

See `README.md` for production deployment guide.
