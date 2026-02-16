# 🚀 Quick Start Guide

## Setup (5 minutes)

### 1. Environment Configuration

Create or update `.env` file in the Food directory with your Neon PostgreSQL credentials:

```bash
# From the Food directory
cp .env.example .env
```

Then edit `.env` with your actual values:

```env
# Use your Neon PostgreSQL connection string (pooler preferred)
DATABASE_URL=postgresql+asyncpg://user:password@ep-xxx-pooler.us-east-1.neon.tech/dbname?sslmode=require

# Your Groq API key for meal generation
GROQ_API_KEY=gsk_your_key_here
```

**To get these values:**
- **GROQ_API_KEY**: Get from [groq.com](https://groq.com) console
- **DATABASE_URL**: Copy from Neon dashboard (use pooler connection)

### 2. Install Dependencies

```bash
cd Food
pip install -r requirements.txt
```

Or install test dependencies specifically:
```bash
pip install pytest pytest-asyncio pytest-cov httpx aiosqlite
```

### 3. Validate Setup

```bash
python validate_setup.py
```

This checks:
- ✓ Environment variables
- ✓ All Python dependencies
- ✓ Database models
- ✓ Core services
- ✓ Neon connection

Output should show all checks passed.

## Running the Application

### Option 1: Run FastAPI Server (Recommended for Testing)

```bash
uvicorn main:app --reload
```

Then visit:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/api/v1/meal-planning/health

### Option 2: Run with Python directly

```bash
python main.py
```

### Option 3: Run with specific host/port

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Category

```bash
# Database models
pytest tests/test_models.py -v

# API endpoints
pytest tests/test_api_endpoints.py -v

# AI meal generation
pytest tests/test_meal_planner.py -v

# Ingredient mapping
pytest tests/test_ingredient_mapper.py -v

# User personalization
pytest tests/test_learning_system.py -v

# Database config
pytest tests/test_config.py -v
```

### Run with Coverage Report

```bash
pytest tests/ --cov=. --cov-report=html
# Open htmlcov/index.html to view report
```

## API Endpoints

Once running, test endpoints:

### 1. Save User Preferences
```bash
curl -X POST http://localhost:8000/api/v1/meal-planning/preferences \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "household_size": 4,
    "budget_level": "moderate",
    "meals_per_day": ["breakfast", "lunch", "dinner"],
    "dietary_restrictions": ["no-pork"]
  }'
```

### 2. Generate Meal Plan
```bash
curl -X POST http://localhost:8000/api/v1/meal-planning/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "duration": "weekly",
    "use_preference_history": true
  }'
```

### 3. Get Ingredients
```bash
curl -X POST http://localhost:8000/api/v1/meal-planning/ingredients \
  -H "Content-Type: application/json" \
  -d '{
    "meal_name": "Jollof Rice",
    "household_size": 4,
    "user_id": "user_123"
  }'
```

### 4. Add to Cart
```bash
curl -X POST http://localhost:8000/api/v1/meal-planning/add-to-cart \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "meal_name": "Jollof Rice",
    "ingredients": [...]
  }'
```

### 5. Submit Feedback
```bash
curl -X POST http://localhost:8000/api/v1/meal-planning/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "meal_name": "Jollof Rice",
    "feedback_type": "viewed",
    "rating": null
  }'
```

### 6. Get Recommendations
```bash
curl -X GET http://localhost:8000/api/v1/meal-planning/recommendations/user_123?count=5
```

### 7. Health Check
```bash
curl http://localhost:8000/api/v1/meal-planning/health
```

## Project Structure

```
Food/
├── main.py                    # FastAPI application entry point
├── api_endpoints.py          # All 8 REST endpoints
├── config.py                 # Database configuration (AsyncSession)
├── models.py                 # 9 SQLModel database models
├── meal_planner.py          # AI meal generation (ChatGroq)
├── ingredient_mapper.py      # 4-tier product mapping
├── learning_system.py        # User personalization
├── validate_setup.py         # System health check
├── main.py                   # FastAPI app entry point
├── requirements.txt          # Dependencies
├── pytest.ini               # Pytest configuration
├── .env.example             # Environment template
├── tests/
│   ├── conftest.py          # Fixtures & dummy data
│   ├── test_models.py       # Model tests
│   ├── test_config.py       # Database config tests
│   ├── test_api_endpoints.py   # Endpoint tests
│   ├── test_meal_planner.py    # AI generation tests
│   ├── test_ingredient_mapper.py # Mapping tests
│   ├── test_learning_system.py   # Personalization tests
│   └── README.md            # Detailed test documentation
└── README.md               # This file
```

## Database Structure

9 Tables in Neon PostgreSQL:

1. **meal_planning_users** - User accounts from backend
2. **meal_planning_user_preferences** - User preferences & settings
3. **meal_planning_plans** - Generated meal plans
4. **meal_planning_plan_meals** - Individual meals in plans
5. **meal_planning_ingredients** - Ingredients mapped to products
6. **meal_planning_purchase_history** - Past purchases for personalization
7. **meal_planning_feedback** - User interactions & ratings
8. **meal_planning_ingredient_catalog** - Reference ingredient database
9. **meal_planning_templates** - Pre-made meal templates

All tables isolated with `meal_planning_` prefix to avoid conflicts with your backend.

## Integration with Existing Backend

### User ID Flow
```
Your Backend → Send user_id → Meal Planning API → Save to DB
```

User IDs come from your existing backend system. The meal planning system just stores association data.

### Product Catalog Integration
```
Ingredient (AI Generated) → Mapper → Your Product Catalog → QuickMarket
```

Pass your product catalog to `IngredientProductMapper` for ingredient-to-product mapping.

### Cart Integration
```
Selected Ingredients → Cart Builder → Webhook/API → Your Backend Cart
```

The system generates cart ready for integration with your existing shopping cart.

## Troubleshooting

### "DATABASE_URL not set"
```
Solution: 
1. Check .env file exists
2. Add DATABASE_URL to .env
3. Reload application
```

### "asyncpg not installed"
```
Solution:
pip install asyncpg sqlalchemy[asyncio] sqlmodel
```

### "Connection refused"
```
Solution:
1. Check Neon database is running
2. Verify CONNECTION_URL is correct
3. Check firewall/network access
4. Try unpooled connection if pooler fails
```

### Slow Tests
```
Solution:
pytest tests/ -v --durations=10
# Shows slowest tests - usually database operations
```

## Performance Tips

1. **Use pooler connection** for production (10x faster than unpooled)
2. **Enable query caching** in learning system
3. **Index frequently searched fields** (user_id, meal_name)
4. **Batch database operations** where possible

## Security Checklist

- ✓ Never commit `.env` file with real credentials
- ✓ Use environment variables in production  
- ✓ Validate all user inputs (Pydantic handles this)
- ✓ Use HTTPS for API in production
- ✓ Implement request authentication (Firebase, OAuth, etc.)
- ✓ Add rate limiting for production
- ✓ Use parameterized queries (SQLModel does this)

## Next Steps

1. ✅ Run `validate_setup.py` to verify everything works
2. ✅ Start server with `uvicorn main:app --reload`
3. ✅ Test endpoints with provided curl commands
4. ✅ Run test suite with `pytest tests/ -v`
5. ✅ Integrate with your existing backend API
6. ✅ Deploy to production when ready

## Support

For issues:
1. Check [tests/README.md](tests/README.md) for detailed test documentation
2. Run `validate_setup.py` to diagnose environment issues
3. Check test output with `pytest tests/ -v --tb=short`
4. Review FastAPI docs at http://localhost:8000/docs

---

**Ready to go?** Run:
```bash
python validate_setup.py && uvicorn main:app --reload
```

Then visit http://localhost:8000/docs to see interactive API documentation! 🎉
