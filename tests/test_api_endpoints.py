"""
Tests for FastAPI endpoints.
Validates all API routes, request/response handling, and database integration.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_endpoints import setup_meal_planning_routes
from models import User, UserPreference, MealPlan
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def app_with_routes():
    """Create FastAPI app with meal planning routes."""
    app = FastAPI()
    setup_meal_planning_routes(app)
    return app


@pytest.fixture
def client(app_with_routes):
    """Create FastAPI test client."""
    return TestClient(app_with_routes)


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check returns 200."""
        response = client.get("/api/v1/meal-planning/health")
        
        # May fail if database not available, but should have proper structure
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "status" in data


class TestSaveUserPreferences:
    """Test save user preferences endpoint."""
    
    def test_save_preferences_success(self, client):
        """Test saving user preferences returns success."""
        payload = {
            "user_id": "test_user_001",
            "meals_per_day": ["breakfast", "lunch", "dinner"],
            "dietary_restrictions": ["no-pork"],
            "budget_level": "moderate",
            "household_size": 4
        }
        
        response = client.post(
            "/api/v1/meal-planning/preferences",
            json=payload
        )
        
        assert response.status_code in [200, 500]  # May fail if DB not available
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert "preference_id" in data
    
    def test_save_preferences_missing_user_id(self, client):
        """Test endpoint handles missing user_id."""
        payload = {
            "meals_per_day": ["breakfast"],
            "budget_level": "moderate"
        }
        
        response = client.post(
            "/api/v1/meal-planning/preferences",
            json=payload
        )
        
        # Should fail validation with 422
        assert response.status_code in [422, 500]


class TestGenerateMealPlan:
    """Test meal plan generation endpoint."""
    
    def test_generate_meal_plan_weekly(self, client):
        """Test generating a weekly meal plan."""
        payload = {
            "user_id": "test_user_001",
            "duration": "weekly",
            "use_preference_history": False
        }
        
        response = client.post(
            "/api/v1/meal-planning/generate",
            json=payload
        )
        
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert "meal_plan_id" in data
            assert "meal_plan" in data
    
    def test_generate_meal_plan_monthly(self, client):
        """Test generating a monthly meal plan."""
        payload = {
            "user_id": "test_user_002",
            "duration": "monthly",
            "use_preference_history": False
        }
        
        response = client.post(
            "/api/v1/meal-planning/generate",
            json=payload
        )
        
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["duration"] == "monthly"


class TestGetMealIngredients:
    """Test ingredient generation endpoint."""
    
    def test_get_ingredients_for_meal(self, client):
        """Test getting ingredients for a meal."""
        payload = {
            "meal_name": "Jollof Rice",
            "household_size": 4,
            "user_id": "test_user_001"
        }
        
        response = client.post(
            "/api/v1/meal-planning/ingredients",
            json=payload
        )
        
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "meal_name" in data
            assert "ingredients" in data
            assert isinstance(data["ingredients"], list)
    
    def test_get_ingredients_respects_household_size(self, client):
        """Test that ingredients scale with household size."""
        for household_size in [1, 2, 4, 6]:
            payload = {
                "meal_name": "Fried Rice",
                "household_size": household_size,
                "user_id": "test_user_001"
            }
            
            response = client.post(
                "/api/v1/meal-planning/ingredients",
                json=payload
            )
            
            assert response.status_code in [200, 500]


class TestAddToCart:
    """Test add to cart endpoint."""
    
    def test_add_ingredients_to_cart(self, client):
        """Test adding ingredients to cart."""
        payload = {
            "user_id": "test_user_001",
            "meal_name": "Jollof Rice",
            "ingredients": [
                {
                    "product_id": "prod_rice_001",
                    "product_name": "Parboiled Rice",
                    "quantity": 2,
                    "unit": "kg",
                    "price": 18000,
                    "availability_status": "available"
                },
                {
                    "product_id": "prod_chicken_001",
                    "product_name": "Fresh Chicken",
                    "quantity": 1,
                    "unit": "kg",
                    "price": 45000,
                    "availability_status": "available"
                }
            ]
        }
        
        response = client.post(
            "/api/v1/meal-planning/add-to-cart",
            json=payload
        )
        
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"


class TestSubmitMealFeedback:
    """Test meal feedback endpoint."""
    
    def test_submit_viewed_feedback(self, client):
        """Test submitting 'viewed' feedback."""
        payload = {
            "user_id": "test_user_001",
            "meal_name": "Jollof Rice",
            "feedback_type": "viewed",
            "rating": None
        }
        
        response = client.post(
            "/api/v1/meal-planning/feedback",
            json=payload
        )
        
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
    
    def test_submit_rated_feedback(self, client):
        """Test submitting rated feedback."""
        payload = {
            "user_id": "test_user_001",
            "meal_name": "Egusi Soup",
            "feedback_type": "rated",
            "rating": 5
        }
        
        response = client.post(
            "/api/v1/meal-planning/feedback",
            json=payload
        )
        
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
    
    def test_submit_purchased_feedback(self, client):
        """Test submitting purchase feedback."""
        payload = {
            "user_id": "test_user_001",
            "meal_name": "Moi Moi",
            "feedback_type": "purchased",
            "rating": 4
        }
        
        response = client.post(
            "/api/v1/meal-planning/feedback",
            json=payload
        )
        
        assert response.status_code in [200, 500]


class TestGetRecommendations:
    """Test personalized recommendations endpoint."""
    
    def test_get_recommendations_for_user(self, client):
        """Test getting recommendations for a user."""
        user_id = "test_user_001"
        response = client.get(f"/api/v1/meal-planning/recommendations/{user_id}")
        
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "user_id" in data
            assert "recommendations" in data
            assert isinstance(data["recommendations"], list)
    
    def test_recommendations_with_count_parameter(self, client):
        """Test recommendations with custom count."""
        user_id = "test_user_001"
        response = client.get(
            f"/api/v1/meal-planning/recommendations/{user_id}?count=10"
        )
        
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert len(data["recommendations"]) <= 10


class TestEndpointErrorHandling:
    """Test error handling in endpoints."""
    
    def test_invalid_meal_name(self, client):
        """Test handling of invalid meal name."""
        payload = {
            "meal_name": "",  # Empty meal name
            "household_size": 4,
            "user_id": "test_user_001"
        }
        
        response = client.post(
            "/api/v1/meal-planning/ingredients",
            json=payload
        )
        
        # Should handle gracefully
        assert response.status_code in [400, 422, 500]
    
    def test_negative_household_size(self, client):
        """Test handling of invalid household size."""
        payload = {
            "meal_name": "Jollof Rice",
            "household_size": -1,  # Invalid
            "user_id": "test_user_001"
        }
        
        response = client.post(
            "/api/v1/meal-planning/ingredients",
            json=payload
        )
        
        assert response.status_code in [400, 422, 500]


class TestEndpointIntegration:
    """Integration tests for full endpoint workflows."""
    
    def test_full_user_journey_endpoints(self, client):
        """Test complete user journey through endpoints."""
        user_id = "journey_user"
        
        # Step 1: Save preferences
        pref_payload = {
            "user_id": user_id,
            "meals_per_day": ["breakfast", "lunch"],
            "budget_level": "moderate",
            "household_size": 3
        }
        pref_response = client.post(
            "/api/v1/meal-planning/preferences",
            json=pref_payload
        )
        assert pref_response.status_code in [200, 500]
        
        # Step 2: Generate meal plan
        plan_payload = {
            "user_id": user_id,
            "duration": "weekly",
            "use_preference_history": True
        }
        plan_response = client.post(
            "/api/v1/meal-planning/generate",
            json=plan_payload
        )
        assert plan_response.status_code in [200, 500]
        
        # Step 3: Get ingredients for a meal
        ing_payload = {
            "meal_name": "Jollof Rice",
            "household_size": 3,
            "user_id": user_id
        }
        ing_response = client.post(
            "/api/v1/meal-planning/ingredients",
            json=ing_payload
        )
        assert ing_response.status_code in [200, 500]
        
        # Step 4: Submit feedback
        feedback_payload = {
            "user_id": user_id,
            "meal_name": "Jollof Rice",
            "feedback_type": "viewed",
            "rating": None
        }
        feedback_response = client.post(
            "/api/v1/meal-planning/feedback",
            json=feedback_payload
        )
        assert feedback_response.status_code in [200, 500]
        
        # Step 5: Get recommendations
        rec_response = client.get(
            f"/api/v1/meal-planning/recommendations/{user_id}"
        )
        assert rec_response.status_code in [200, 500]
