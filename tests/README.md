# Meal Planning Tests

This directory contains comprehensive tests for the meal planning system, validating all core components.

## Directory Structure

```
tests/
├── __init__.py              # Tests package
├── conftest.py             # Pytest configuration and shared fixtures
├── test_models.py          # Database model tests (User, MealPlan, etc.)
├── test_config.py          # Database configuration and connection tests
├── test_meal_planner.py    # AI meal generation tests
├── test_ingredient_mapper.py  # Ingredient-to-product mapping tests
├── test_learning_system.py # User personalization and recommendations tests
└── test_api_endpoints.py   # FastAPI endpoint tests
```

## Test Coverage

The test suite covers:

### 1. **Models** (`test_models.py`)
- Model creation and validation
- Field defaults and constraints
- Foreign key relationships
- Complex JSON field handling

### 2. **Database Configuration** (`test_config.py`)
- AsyncSession creation
- Database connection pooling
- CRUD operations (Create, Read, Update, Delete)
- Transaction handling and rollback

### 3. **Meal Planning** (`test_meal_planner.py`)
- Meal plan generation (weekly/monthly)
- Preference-based customization
- Budget constraint handling
- Multi-meal ingredient generation

### 4. **Ingredient Mapping** (`test_ingredient_mapper.py`)
- 4-tier matching algorithm (exact → fuzzy → category → fallback)
- Product catalog integration
- Cart building with availability checking
- Pricing calculations

### 5. **Learning System** (`test_learning_system.py`)
- User profile tracking
- Feedback recording (viewed, selected, rated, purchased)
- Personalized recommendations
- Learning from user interactions

### 6. **API Endpoints** (`test_api_endpoints.py`)
- All 8 REST endpoints
- Request/response validation
- Error handling
- Full user journey integration tests

## Running Tests

### Prerequisites

1. Install test dependencies:
```bash
pip install pytest pytest-asyncio httpx aiosqlite
```

2. Configure environment (optional for unit tests):
```bash
cp .env.example .env
# Edit .env with your actual database URL (if testing with Neon)
```

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test File

```bash
pytest tests/test_models.py
pytest tests/test_api_endpoints.py
```

### Run Specific Test Class

```bash
pytest tests/test_models.py::TestUserModel
pytest tests/test_api_endpoints.py::TestHealthEndpoint
```

### Run Specific Test

```bash
pytest tests/test_models.py::TestUserModel::test_create_user
```

### Run with Verbose Output

```bash
pytest tests/ -v
```

### Run with Coverage Report

```bash
pip install pytest-cov
pytest tests/ --cov=. --cov-report=html
```

### Run Only Async Tests

```bash
pytest tests/ -m asyncio
```

### Run Only Unit Tests (No Integration)

```bash
pytest tests/ -m "not integration"
```

## Fixtures and Dummy Data

The `conftest.py` file provides reusable fixtures simulating data from your existing backend:

### User Fixtures
- `dummy_user_data` - Regular user from backend
- `dummy_new_user_data` - New user from backend
- `user_in_db` - User created in test database
- `user_with_preferences` - User with saved preferences
- `user_with_meal_plan` - User with generated meal plan

### Data Fixtures
- `dummy_user_preferences` - Sample user preferences
- `dummy_product_catalog` - 10 QuickMarket products (proteins, vegetables, grains, seasonings)
- `dummy_purchase_history` - Sample purchase history for personalization
- `dummy_meal_templates` - 5 Nigerian meal templates

### Response Fixtures
- `expected_meal_plan_response` - Expected API response structure
- `expected_ingredients_response` - Expected ingredients response

### Database Fixtures
- `test_engine` - SQLite in-memory database engine (for testing)
- `test_session` - Async session for database operations

## Example Test Usage

### Testing Model Creation

```python
@pytest.mark.asyncio
async def test_create_user(self, test_session, dummy_user_data):
    """Test creating a user."""
    user = User(**dummy_user_data)
    test_session.add(user)
    await test_session.commit()
    
    result = await test_session.get(User, user.user_id)
    assert result is not None
```

### Testing API Endpoints

```python
def test_health_check(self, client):
    """Test health check endpoint."""
    response = client.get("/api/v1/meal-planning/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
```

### Testing with Dummy Data

```python
@pytest.mark.asyncio
async def test_user_with_preferences(self, test_session, user_with_preferences):
    """Test user with saved preferences."""
    user, pref = user_with_preferences
    assert pref.budget_level == "moderate"
    assert pref.meal_duration == "weekly"
```

## Testing with Neon PostgreSQL

To test with actual Neon connection:

1. Set `DATABASE_URL` in `.env`:
```
DATABASE_URL=postgresql+asyncpg://user:password@ep-xxx-pooler.../dbname
```

2. Some tests will automatically use Neon if available, others use SQLite

3. Run connection test:
```bash
pytest tests/test_config.py::TestDatabaseConfig::test_engine_creation -v
```

## Expected Results

- ✅ **Models**: All 9 table models validate correctly
- ✅ **Database**: AsyncSession works with connection pooling
- ✅ **AI Logic**: Meal generation respects household size and budget
- ✅ **Mapping**: 4-tier algorithm finds products 95%+ of time
- ✅ **API**: All 8 endpoints return valid responses
- ✅ **Learning**: User profiles track interactions correctly

## CI/CD Integration

Add to your GitHub Actions workflow:

```yaml
- name: Run Tests
  run: |
    pip install pytest pytest-asyncio httpx aiosqlite
    pytest tests/ -v --tb=short
```

## Debugging Tests

### Enable SQL Logging

In `conftest.py`, change:
```python
engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=True  # See all SQL queries
)
```

### Print Test Variables

```python
@pytest.mark.asyncio
async def test_something(self, test_session):
    print("\n" + "="*50)
    print(f"Session: {test_session}")
    print("="*50)
    # ... rest of test
```

### Run with Debugger

```bash
pytest tests/ --pdb  # Drop into pdb on failure
pytest tests/ --pdbcls=IPython.terminal.debugger:Pdb  # Use IPython
```

## Common Issues

### "DATABASE_URL not set"
Solution: Set `DATABASE_URL` in `.env` or as environment variable

### "asyncpg not installed"
Solution: `pip install asyncpg sqlalchemy[asyncio]`

### "Cannot create new event loop"
Solution: Use `pytest-asyncio` and set `asyncio_mode = auto` in `pytest.ini`

### Neon Connection Timeout
Solution: Check internet connection and Neon dashboard for active databases

## Contributing Tests

When adding new features:

1. Write tests in appropriate `test_*.py` file
2. Use fixtures from `conftest.py`
3. Follow naming convention: `test_<feature>_<scenario>`
4. Add docstrings explaining test purpose
5. Run full suite: `pytest tests/ -v`

## Support

For issues:
1. Check test output carefully
2. Run with `-v` for verbose output
3. Try specific test: `pytest tests/test_*.py::TestClass::test_method -v`
4. Check `.env` configuration
5. Verify database connectivity

---

**Last Updated**: February 2026
**Test Suite Version**: 1.0.0
