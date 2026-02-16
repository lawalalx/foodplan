"""
Pytest configuration and fixtures for meal planning tests.
Includes dummy data simulating the existing backend.
"""
import pytest
import os
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel, select
from typing import AsyncGenerator

# Import models
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import (
    User, UserPreference, MealPlan, PlanMeal, PlanMealIngredient,
    PurchaseHistory, MealFeedback, Ingredient, MealTemplate
)


# ============================================================================
# TEST DATABASE SETUP
# ============================================================================

# Use SQLite for testing (in-memory or file-based)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    """Create test engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    async with async_session() as session:
        yield session


# ============================================================================
# DUMMY DATA FIXTURES (Simulating Backend)
# ============================================================================

@pytest.fixture
def dummy_user_data():
    """Simulated user data from existing backend."""
    return {
        "user_id": "user_12345",
        "phone_number": "+2348012345678",
        "household_size": 4,
        "is_new_user": False,
    }


@pytest.fixture
def dummy_new_user_data():
    """Simulated new user from existing backend."""
    return {
        "user_id": "user_67890",
        "phone_number": "+2348087654321",
        "household_size": 2,
        "is_new_user": True,
    }


@pytest.fixture
def dummy_user_preferences():
    """Simulated user preferences."""
    return {
        "meal_duration": "weekly",
        "meals_per_day": "breakfast,lunch,dinner",
        "dietary_restrictions": "no-pork,no-alcohol",
        "meal_types": "nigerian,continental",
        "budget_level": "moderate"
    }


@pytest.fixture
def dummy_product_catalog():
    """Simulated product catalog from QuickMarket backend."""
    return [
        # Proteins
        {
            "product_id": "prod_chicken_001",
            "product_name": "Fresh Chicken",
            "category": "proteins",
            "price": 45000,  # NGN
            "unit": "kg",
            "availability": "available"
        },
        {
            "product_id": "prod_beef_001",
            "product_name": "Beef - Ground",
            "category": "proteins",
            "price": 35000,
            "unit": "kg",
            "availability": "available"
        },
        {
            "product_id": "prod_fish_001",
            "product_name": "Fresh Fish",
            "category": "proteins",
            "price": 55000,
            "unit": "kg",
            "availability": "available"
        },
        # Vegetables
        {
            "product_id": "prod_tomato_001",
            "product_name": "Fresh Tomatoes",
            "category": "vegetables",
            "price": 8000,
            "unit": "kg",
            "availability": "available"
        },
        {
            "product_id": "prod_onion_001",
            "product_name": "Red Onions",
            "category": "vegetables",
            "price": 6000,
            "unit": "kg",
            "availability": "available"
        },
        {
            "product_id": "prod_pepper_001",
            "product_name": "Bell Peppers",
            "category": "vegetables",
            "price": 10000,
            "unit": "kg",
            "availability": "available"
        },
        # Grains
        {
            "product_id": "prod_rice_001",
            "product_name": "Parboiled Rice",
            "category": "grains",
            "price": 18000,
            "unit": "kg",
            "availability": "available"
        },
        {
            "product_id": "prod_garri_001",
            "product_name": "Garri",
            "category": "grains",
            "price": 12000,
            "unit": "kg",
            "availability": "available"
        },
        # Spices & Seasonings
        {
            "product_id": "prod_salt_001",
            "product_name": "Sea Salt",
            "category": "seasonings",
            "price": 2000,
            "unit": "kg",
            "availability": "available"
        },
        {
            "product_id": "prod_garlic_001",
            "product_name": "Garlic Powder",
            "category": "seasonings",
            "price": 5000,
            "unit": "kg",
            "availability": "available"
        },
    ]


@pytest.fixture
def dummy_purchase_history():
    """Simulated purchase history for user personalization."""
    return [
        {
            "product_id": "prod_chicken_001",
            "product_name": "Fresh Chicken",
            "quantity": 2,
            "unit": "kg",
            "price": 45000,
            "ingredient_category": "proteins",
            "purchase_date": datetime.utcnow() - timedelta(days=7)
        },
        {
            "product_id": "prod_rice_001",
            "product_name": "Parboiled Rice",
            "quantity": 5,
            "unit": "kg",
            "price": 18000,
            "ingredient_category": "grains",
            "purchase_date": datetime.utcnow() - timedelta(days=5)
        },
        {
            "product_id": "prod_tomato_001",
            "product_name": "Fresh Tomatoes",
            "quantity": 3,
            "unit": "kg",
            "price": 8000,
            "ingredient_category": "vegetables",
            "purchase_date": datetime.utcnow() - timedelta(days=3)
        },
    ]


@pytest.fixture
def dummy_meal_templates():
    """Meal templates for fast meal generation."""
    return [
        {
            "meal_name": "Jollof Rice",
            "cuisine_type": "nigerian",
            "difficulty_level": "medium",
            "estimated_cook_time": 45,
            "calories": 450,
            "protein_g": 8,
            "base_ingredients": {
                "rice": {"quantity": 2, "unit": "cups"},
                "tomato": {"quantity": 3, "unit": "pieces"},
                "onion": {"quantity": 1, "unit": "piece"},
                "chicken": {"quantity": 1, "unit": "kg"}
            },
            "is_vegetarian": False,
            "popularity_score": 9.5
        },
        {
            "meal_name": "Egusi Soup",
            "cuisine_type": "nigerian",
            "difficulty_level": "medium",
            "estimated_cook_time": 60,
            "calories": 350,
            "protein_g": 12,
            "base_ingredients": {
                "egusi": {"quantity": 200, "unit": "g"},
                "greens": {"quantity": 500, "unit": "g"},
                "beef": {"quantity": 0.5, "unit": "kg"},
                "palm_oil": {"quantity": 0.25, "unit": "liter"}
            },
            "is_vegetarian": False,
            "popularity_score": 9.0
        },
        {
            "meal_name": "Moi Moi",
            "cuisine_type": "nigerian",
            "difficulty_level": "easy",
            "estimated_cook_time": 30,
            "calories": 280,
            "protein_g": 15,
            "base_ingredients": {
                "beans": {"quantity": 500, "unit": "g"},
                "eggs": {"quantity": 3, "unit": "pieces"},
                "onion": {"quantity": 0.5, "unit": "piece"}
            },
            "is_vegetarian": True,
            "popularity_score": 8.5
        },
        {
            "meal_name": "Pepper Soup",
            "cuisine_type": "nigerian",
            "difficulty_level": "easy",
            "estimated_cook_time": 30,
            "calories": 180,
            "protein_g": 18,
            "base_ingredients": {
                "fish": {"quantity": 1, "unit": "kg"},
                "scotch_bonnets": {"quantity": 2, "unit": "pieces"},
                "onion": {"quantity": 0.5, "unit": "piece"}
            },
            "is_vegetarian": False,
            "popularity_score": 8.0
        },
        {
            "meal_name": "Fried Rice",
            "cuisine_type": "continental",
            "difficulty_level": "easy",
            "estimated_cook_time": 25,
            "calories": 420,
            "protein_g": 10,
            "base_ingredients": {
                "rice": {"quantity": 3, "unit": "cups"},
                "vegetables": {"quantity": 2, "unit": "cups"},
                "eggs": {"quantity": 2, "unit": "pieces"}
            },
            "is_vegetarian": True,
            "popularity_score": 9.0
        }
    ]


@pytest.fixture
async def user_in_db(test_session, dummy_user_data):
    """Create a test user in the database."""
    user = User(**dummy_user_data)
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest.fixture
async def user_with_preferences(test_session, user_in_db, dummy_user_preferences):
    """Create user with saved preferences."""
    preference = UserPreference(
        user_id=user_in_db.user_id,
        **dummy_user_preferences
    )
    test_session.add(preference)
    await test_session.commit()
    await test_session.refresh(preference)
    return user_in_db, preference


@pytest.fixture
async def user_with_meal_plan(test_session, user_in_db):
    """Create user with a generated meal plan."""
    meal_plan = MealPlan(
        user_id=user_in_db.user_id,
        duration="weekly",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=7),
        plan_content={
            "monday": [
                {"meal": "Jollof Rice", "type": "lunch"},
                {"meal": "Pepper Soup", "type": "dinner"}
            ],
            "tuesday": [
                {"meal": "Egusi Soup", "type": "lunch"},
                {"meal": "Fried Rice", "type": "dinner"}
            ]
        },
        used=False
    )
    test_session.add(meal_plan)
    await test_session.commit()
    await test_session.refresh(meal_plan)
    return user_in_db, meal_plan


@pytest.fixture
async def user_with_purchase_history(test_session, user_in_db, dummy_purchase_history):
    """Create user with purchase history."""
    for purchase_data in dummy_purchase_history:
        purchase = PurchaseHistory(
            user_id=user_in_db.user_id,
            **purchase_data
        )
        test_session.add(purchase)
    
    await test_session.commit()
    
    purchases = await test_session.execute(
        select(PurchaseHistory).where(PurchaseHistory.user_id == user_in_db.user_id)
    )
    return user_in_db, purchases.scalars().all()


@pytest.fixture
def expected_meal_plan_response():
    """Expected structure of a meal plan response."""
    return {
        "status": "success",
        "meal_plan_id": "uuid",
        "duration": "weekly",
        "meal_plan": {"type": "dict"},
        "next_action": "View meals or select one to get ingredients"
    }


@pytest.fixture
def expected_ingredients_response():
    """Expected structure of an ingredients response."""
    return {
        "meal_name": "Jollof Rice",
        "household_size": 4,
        "ingredients": [{"type": "list"}],
        "total_estimated_cost": 150000,  # NGN
        "unavailable_count": 0
    }
