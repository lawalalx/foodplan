# MEAL PLANNING SYSTEM - IMPLEMENTATION GUIDE

## Overview
This guide shows how to integrate the meal planning system into your FastAPI application.

## File Structure
```
Food/
├── models.py                  # Database models
├── meal_planner.py            # AI meal plan generation
├── ingredient_mapper.py       # Ingredient → product mapping
├── learning_system.py         # User behavior tracking & personalization
├── api_endpoints.py           # FastAPI routes
├── end_to_end_test.py         # Complete workflow demo
├── SYSTEM_ARCHITECTURE.md     # Architecture documentation
└── README.md                  # This guide
```

## Quick Start

### 1. Import & Initialize

```python
from fastapi import FastAPI
from Food.api_endpoints import setup_meal_planning_routes, setup_health_routes

app = FastAPI(title="QuickMarket API")

# Register meal planning routes
setup_meal_planning_routes(app)
setup_health_routes(app)
```

### 2. Run End-to-End Test

```bash
cd Food
python end_to_end_test.py
```

This demonstrates:
- New user preference capture
- Meal plan generation
- Ingredient generation
- Product mapping
- Cart building
- Learning system

## Core System Components

### 1. MealPlanGenerator
Generates AI-powered meal plans using ChatGroq.

**Usage:**
```python
from Food.meal_planner import MealPlanGenerator

generator = MealPlanGenerator()

# For new user (preference-based)
meal_plan = generator.generate_meal_plan(
    user_id="user_123",
    duration="weekly",
    meal_preference={
        "meals_per_day": ["breakfast", "lunch", "dinner"],
        "dietary_restrictions": ["vegetarian"],
        "meal_types": ["nigerian"],
        "budget_level": "moderate"
    },
    household_size=3
)

# For returning user (history-based)
meal_plan = generator.generate_meal_plan(
    user_id="user_456",
    duration="monthly",
    purchase_history=[
        {"product_name": "Rice", "category": "grains"},
        {"product_name": "Beans", "category": "legumes"}
    ],
    household_size=2,
    budget_level="budget-friendly"
)
```

### 2. IngredientGenerator
Generate ingredient lists for meals with portion adjustments.

**Usage:**
```python
from Food.meal_planner import IngredientGenerator

generator = IngredientGenerator()

ingredients = generator.generate_ingredients(
    meal_name="Egusi Soup",
    household_size=3,
    servings=1
)

# Returns:
# [
#   {"name": "Egusi seeds", "quantity": 500, "unit": "g"},
#   {"name": "Palm oil", "quantity": 250, "unit": "ml"},
#   ...
# ]
```

### 3. IngredientProductMapper
Maps ingredients to QuickMarket products.

**Usage:**
```python
from Food.ingredient_mapper import IngredientProductMapper

# Initialize with product catalog
products = [
    {
        "id": "prod_001",
        "name": "Ground Egusi (500g)",
        "category": "seasonings",
        "price": 2500,
        "availability_status": "available"
    },
    # ... more products
]

mapper = IngredientProductMapper(product_catalog=products)

# Map an ingredient to a product
mapping = mapper.map_ingredient_to_product(
    ingredient_name="Egusi seeds",
    quantity=500,
    unit="g"
)

# Returns:
# {
#   "ingredient_name": "Egusi seeds",
#   "quantity": 500,
#   "unit": "g",
#   "mapped_product_id": "prod_001",
#   "product_name": "Ground Egusi (500g)",
#   "product_price": 2500,
#   "availability_status": "available",
#   "confidence_score": 0.95
# }
```

### 4. CartBuilder
Build shopping cart from ingredients.

**Usage:**
```python
from Food.ingredient_mapper import CartBuilder

mapped_ingredients = [...]  # From ingredient mapper

cart_update = CartBuilder.add_ingredients_to_cart(
    mapped_ingredients=mapped_ingredients,
    user_cart_id="cart_user_123"
)

# Returns:
# {
#   "added_count": 6,
#   "skipped_count": 1,
#   "total_amount": 15000,
#   "items": [...]
# }
```

### 5. UserLearningSystem
Track user behavior and generate personalized recommendations.

**Usage:**
```python
from Food.learning_system import UserLearningSystem

learning = UserLearningSystem()

# Record user interactions
learning.record_feedback(
    user_id="user_123",
    meal_name="Egusi Soup",
    feedback_type="viewed"  # "viewed"|"selected"|"purchased"|"cooked"
)

learning.record_feedback(
    user_id="user_123",
    meal_name="Egusi Soup",
    feedback_type="selected"
)

# Get personalized recommendations
recommendations = learning.get_recommendations(
    user_id="user_123",
    count=5,
    use_history=True
)

# Returns:
# [
#   {
#     "meal_name": "Egusi Soup",
#     "reason": "Similar to your favorites",
#     "confidence": 0.85,
#     "popularity_score": 0.92
#   },
#   ...
# ]

# Get user insights
insights = learning.get_user_insights(user_id="user_123")
# {
#   "total_interactions": 42,
#   "favorite_meals": ["Jollof", "Egusi"],
#   "average_rating": 4.2,
#   ...
# }
```

## API Endpoints

### Save User Preferences
```
POST /api/v1/meal-planning/preferences
Content-Type: application/json

{
  "user_id": "user_123",
  "meals_per_day": ["breakfast", "lunch", "dinner"],
  "dietary_restrictions": ["vegetarian"],
  "meal_types": ["nigerian", "international"],
  "budget_level": "moderate",
  "household_size": 3
}

Response:
{
  "status": "success",
  "preference_id": "pref_456",
  "message": "Preferences saved successfully"
}
```

### Generate Meal Plan
```
POST /api/v1/meal-planning/generate
Content-Type: application/json

{
  "user_id": "user_123",
  "duration": "weekly",
  "use_preference_history": true
}

Response:
{
  "status": "success",
  "meal_plan_id": "plan_789",
  "duration": "weekly",
  "meal_plan": {
    "day_1": {
      "breakfast": "Pap & Akara",
      "lunch": "Egusi Soup & Swallow",
      "dinner": "Jollof Rice & Stew"
    },
    ...
  }
}
```

### Get Meal Ingredients
```
POST /api/v1/meal-planning/ingredients
Content-Type: application/json

{
  "meal_name": "Egusi Soup",
  "household_size": 3,
  "meal_plan_id": "plan_789"
}

Response:
{
  "meal_name": "Egusi Soup",
  "household_size": 3,
  "ingredients": [
    {
      "ingredient_name": "Egusi seeds",
      "quantity": 500,
      "unit": "g",
      "mapped_product_id": "prod_001",
      "product_name": "Ground Egusi (500g)",
      "product_price": 2500,
      "availability_status": "available",
      "confidence_score": 0.95
    },
    ...
  ],
  "total_estimated_cost": 15000,
  "unavailable_count": 0
}
```

### Add to Cart
```
POST /api/v1/meal-planning/add-to-cart
Content-Type: application/json

{
  "user_id": "user_123",
  "meal_plan_id": "plan_789",
  "meal_name": "Egusi Soup",
  "ingredients": [...]
}

Response:
{
  "status": "success",
  "message": "Added 6 items to your cart",
  "cart_update": {
    "added_count": 6,
    "skipped_count": 1,
    "total_amount": 15000,
    "items": [...]
  }
}
```

### Record Feedback
```
POST /api/v1/meal-planning/feedback
Content-Type: application/json

{
  "user_id": "user_123",
  "meal_plan_id": "plan_789",
  "meal_name": "Egusi Soup",
  "feedback_type": "purchased",
  "rating": 5
}

Response:
{
  "status": "success",
  "feedback_id": "feedback_111",
  "message": "Feedback recorded successfully"
}
```

### Get User History
```
GET /api/v1/meal-planning/history/user_123

Response:
{
  "user_id": "user_123",
  "meal_plans": [...],
  "preferences": {...},
  "meal_count": 25
}
```

### Get Recommendations
```
GET /api/v1/meal-planning/recommendations/user_123

Response:
{
  "user_id": "user_123",
  "recommendations": [
    {
      "meal_name": "Egusi Soup",
      "reason": "Similar to your favorites",
      "confidence": 0.85
    },
    ...
  ]
}
```

## Integration with Main App

### Option 1: Include in food.py
```python
# In Food/food.py
from .api_endpoints import setup_meal_planning_routes

app = FastAPI(title="Kittchens AI API")

# ... existing setup ...

# Register meal planning routes
setup_meal_planning_routes(app)
```

### Option 2: Separate Blueprint
```python
# In main app
from Food.api_endpoints import setup_meal_planning_routes

app = FastAPI()

setup_meal_planning_routes(app)
```

## Database Setup

### Define Database Session
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from Food.models import Base

DATABASE_URL = "postgresql://user:password@localhost/quickmarket"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)
```

### Create Alembic Migration
```bash
alembic init alembic
alembic revision --autogenerate -m "Add meal planning tables"
alembic upgrade head
```

## Configuration

### Environment Variables (.env)
```env
# LLM Configuration
GROQ_API_KEY=xxxxx
GROQ_MODEL=mixtral-8x7b-32768

# Database
DATABASE_URL=postgresql://user:password@localhost/quickmarket

# Product Catalog API
PRODUCT_CATALOG_API=https://api.quickmarket.com/products
PRODUCT_API_KEY=xxxxx

# Redis (optional)
REDIS_URL=redis://localhost:6379
```

### Settings Class
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    groq_api_key: str
    groq_model: str = "mixtral-8x7b-32768"
    database_url: str
    product_catalog_api: str
    redis_url: str = "redis://localhost:6379"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Testing

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest Food/test_meal_planner.py -v
pytest Food/test_ingredient_mapper.py -v
pytest Food/test_learning_system.py -v

# Run end-to-end demo
python Food/end_to_end_test.py
```

### Sample Test
```python
import pytest
from Food.meal_planner import MealPlanGenerator

@pytest.mark.asyncio
async def test_meal_plan_generation():
    generator = MealPlanGenerator()
    
    meal_plan = generator.generate_meal_plan(
        user_id="test_user",
        duration="weekly",
        meal_preference={
            "meals_per_day": ["breakfast", "lunch", "dinner"],
            "meal_types": ["nigerian"]
        },
        household_size=2
    )
    
    assert meal_plan is not None
    assert "day_1" in meal_plan
```

## Performance Optimization

### Caching
```python
from functools import lru_cache

class MealPlanGenerator:
    @lru_cache(maxsize=100)
    def _load_meal_templates(self):
        # Load templates once
        ...
```

### Async Support
```python
from fastapi import BackgroundTasks

@app.post("/api/v1/meal-planning/generate")
async def generate_meal_plan(request, background_tasks: BackgroundTasks):
    # Quick response
    meal_plan_id = str(uuid.uuid4())
    
    # Generate in background
    background_tasks.add_task(actually_generate, meal_plan_id)
    
    return {"meal_plan_id": meal_plan_id, "status": "generating"}
```

## Monitoring & Logging

### Structured Logging
```python
import logging
import json

logger = logging.getLogger(__name__)

def log_meal_plan_generation(user_id, duration, success):
    logger.info(json.dumps({
        "event": "meal_plan_generated",
        "user_id": user_id,
        "duration": duration,
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }))
```

### Metrics
```python
from prometheus_client import Counter, Histogram

meal_plans_generated = Counter('meal_plans_total', 'Total meal plans generated')
generation_time = Histogram('meal_plan_generation_seconds', 'Generation duration')

with generation_time.time():
    meal_plan = generator.generate_meal_plan(...)

meal_plans_generated.inc()
```

## Troubleshooting

### LLM Not Responding
- Check GROQ_API_KEY is set
- Verify network connectivity
- Check rate limits
- Add retry logic

### Product Mapping Failures
- Ensure product catalog is loaded
- Check category mappings
- Verify ingredient normalization
- Add more fuzzy match examples

### Database Errors
- Check database connection URL
- Verify migrations are run
- Check table permissions
- Review transaction handling

## Next Steps

1. **Database Integration**
   - Set up PostgreSQL
   - Run Alembic migrations
   - Seed meal templates

2. **Product Catalog**
   - Connect to QuickMarket API
   - Set up product sync
   - Build search index

3. **Testing & QA**
   - Write unit tests
   - Run integration tests
   - Load testing (1000 req/min)

4. **Deployment**
   - Configure staging environment
   - Set up monitoring
   - Deploy to production

5. **Optimization**
   - Profile slow endpoints
   - Implement caching
   - Optimize queries
   - Add rate limiting

## Support

For issues or questions:
1. Check SYSTEM_ARCHITECTURE.md
2. Review end_to_end_test.py for examples
3. Check error logs
4. Contact development team
