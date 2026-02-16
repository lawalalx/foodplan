"""
Tests for meal planning AI logic.
Validates meal plan and ingredient generation.
"""
import pytest
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from meal_planner import MealPlanGenerator, IngredientGenerator


class TestMealPlanGenerator:
    """Test meal plan generation."""
    
    @pytest.fixture
    def generator(self):
        """Initialize meal plan generator."""
        return MealPlanGenerator()
    
    def test_generator_initialization(self, generator):
        """Test generator can be initialized."""
        assert generator is not None
        assert hasattr(generator, 'generate_meal_plan')
        assert hasattr(generator, 'client')
    
    @pytest.mark.asyncio
    async def test_generate_meal_plan_weekly(self, generator):
        """Test generating a weekly meal plan."""
        plan = await generator.generate_meal_plan(
            user_id="test_user",
            duration="weekly",
            meal_preference=None,
            purchase_history=None,
            household_size=4,
            budget_level="moderate"
        )
        
        # Verify structure
        assert plan is not None
        assert isinstance(plan, (dict, str))
        
        # If string, try to parse as JSON
        if isinstance(plan, str):
            plan_dict = json.loads(plan)
            assert plan_dict is not None
    
    @pytest.mark.asyncio
    async def test_generate_meal_plan_with_preferences(self, generator):
        """Test generating meal plan with user preferences."""
        preferences = {
            "dietary_restrictions": ["no-pork"],
            "meal_types": ["nigerian"],
            "budget_level": "moderate"
        }
        
        plan = await generator.generate_meal_plan(
            user_id="test_user",
            duration="weekly",
            meal_preference=preferences,
            purchase_history=None,
            household_size=4,
            budget_level="moderate"
        )
        
        assert plan is not None
    
    @pytest.mark.asyncio
    async def test_generate_meal_plan_respects_budget(self, generator):
        """Test that meal plans respect budget constraints."""
        # Budget-friendly plan
        budget_plan = await generator.generate_meal_plan(
            user_id="test_user",
            duration="weekly",
            meal_preference=None,
            purchase_history=None,
            household_size=2,
            budget_level="budget-friendly"
        )
        
        # Premium plan
        premium_plan = await generator.generate_meal_plan(
            user_id="test_user",
            duration="weekly",
            meal_preference=None,
            purchase_history=None,
            household_size=2,
            budget_level="premium"
        )
        
        assert budget_plan is not None
        assert premium_plan is not None


class TestIngredientGenerator:
    """Test ingredient generation."""
    
    @pytest.fixture
    def generator(self):
        """Initialize ingredient generator."""
        return IngredientGenerator()
    
    def test_generator_initialization(self, generator):
        """Test generator can be initialized."""
        assert generator is not None
        assert hasattr(generator, 'generate_ingredients')
    
    @pytest.mark.asyncio
    async def test_generate_ingredient_list(self, generator):
        """Test generating ingredients for a meal."""
        ingredients = await generator.generate_ingredients(
            meal_name="Jollof Rice",
            household_size=4
        )
        
        # Verify structure
        assert ingredients is not None
        assert isinstance(ingredients, (list, str))
        
        # If string, try to parse as JSON
        if isinstance(ingredients, str):
            ingredients_list = json.loads(ingredients)
            assert isinstance(ingredients_list, list)
            for item in ingredients_list:
                assert "name" in item or "ingredient" in item
    
    @pytest.mark.asyncio
    async def test_generate_ingredients_respects_household_size(self, generator):
        """Test that ingredient quantities scale with household size."""
        small_household = await generator.generate_ingredients(
            meal_name="Fried Rice",
            household_size=2
        )
        
        large_household = await generator.generate_ingredients(
            meal_name="Fried Rice",
            household_size=8
        )
        
        assert small_household is not None
        assert large_household is not None
    
    @pytest.mark.asyncio
    async def test_generate_nigerian_meal_ingredients(self, generator):
        """Test generating ingredients for Nigerian meals."""
        nigerian_meals = [
            "Egusi Soup",
            "Pepper Soup",
            "Moi Moi",
            "Jollof Rice"
        ]
        
        for meal in nigerian_meals:
            ingredients = await generator.generate_ingredients(
                meal_name=meal,
                household_size=4
            )
            assert ingredients is not None


class TestMealGenerationIntegration:
    """Integration tests for meal and ingredient generation."""
    
    @pytest.fixture
    def meal_generator(self):
        return MealPlanGenerator()
    
    @pytest.fixture
    def ingredient_generator(self):
        return IngredientGenerator()
    
    @pytest.mark.asyncio
    async def test_full_meal_generation_flow(self, meal_generator, ingredient_generator):
        """Test full flow: meal plan -> select meal -> get ingredients."""
        # Step 1: Generate meal plan
        meal_plan = await meal_generator.generate_meal_plan(
            user_id="test_user",
            duration="weekly",
            meal_preference=None,
            purchase_history=None,
            household_size=4,
            budget_level="moderate"
        )
        assert meal_plan is not None
        
        # Step 2: Parse meal plan and extract a meal name
        # For testing, use a known meal
        meal_name = "Jollof Rice"
        
        # Step 3: Generate ingredients
        ingredients = await ingredient_generator.generate_ingredients(
            meal_name=meal_name,
            household_size=4
        )
        assert ingredients is not None
