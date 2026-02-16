"""
Tests for SQLModel database models.
Validates model creation, relationships, and constraints.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from models import (
    User, UserPreference, MealPlan, PlanMeal, PlanMealIngredient,
    PurchaseHistory, MealFeedback, Ingredient, MealTemplate
)


class TestUserModel:
    """Test User model."""
    
    @pytest.mark.asyncio
    async def test_create_user(self, test_session, dummy_user_data):
        """Test creating a user."""
        user = User(**dummy_user_data)
        test_session.add(user)
        await test_session.commit()
        
        # Verify
        result = await test_session.get(User, user.user_id)
        assert result is not None
        assert result.user_id == dummy_user_data["user_id"]
        assert result.household_size == dummy_user_data["household_size"]
    
    @pytest.mark.asyncio
    async def test_user_defaults(self, test_session):
        """Test user model defaults."""
        user = User(user_id="test_user")
        test_session.add(user)
        await test_session.commit()
        
        result = await test_session.get(User, user.user_id)
        assert result.household_size == 1
        assert result.is_new_user is True
        assert result.created_at is not None
        assert result.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_user_phone_number(self, test_session):
        """Test user with phone number."""
        user = User(
            user_id="phone_user",
            phone_number="+2348012345678"
        )
        test_session.add(user)
        await test_session.commit()
        
        result = await test_session.get(User, user.user_id)
        assert result.phone_number == "+2348012345678"


class TestUserPreferenceModel:
    """Test UserPreference model."""
    
    @pytest.mark.asyncio
    async def test_create_preference(self, test_session, user_in_db, dummy_user_preferences):
        """Test creating user preferences."""
        pref = UserPreference(
            user_id=user_in_db.user_id,
            **dummy_user_preferences
        )
        test_session.add(pref)
        await test_session.commit()
        
        # Verify
        result = await test_session.get(UserPreference, pref.preference_id)
        assert result is not None
        assert result.user_id == user_in_db.user_id
        assert result.budget_level == "moderate"
    
    @pytest.mark.asyncio
    async def test_preference_defaults(self, test_session, user_in_db):
        """Test preference defaults."""
        pref = UserPreference(user_id=user_in_db.user_id)
        test_session.add(pref)
        await test_session.commit()
        
        result = await test_session.get(UserPreference, pref.preference_id)
        assert result.meal_duration == "weekly"
        assert result.meals_per_day == "breakfast,lunch,dinner"
    
    @pytest.mark.asyncio
    async def test_user_preference_relationship(self, test_session, user_with_preferences):
        """Test user-preference relationship."""
        user, pref = user_with_preferences
        
        # Reload user with relationships
        result = await test_session.get(User, user.user_id)
        assert len(result.preferences) == 1
        assert result.preferences[0].preference_id == pref.preference_id


class TestMealPlanModel:
    """Test MealPlan model."""
    
    @pytest.mark.asyncio
    async def test_create_meal_plan(self, test_session, user_in_db):
        """Test creating a meal plan."""
        meal_plan = MealPlan(
            user_id=user_in_db.user_id,
            duration="weekly",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
            plan_content={"monday": [{"meal": "Jollof Rice", "type": "lunch"}]},
            used=False
        )
        test_session.add(meal_plan)
        await test_session.commit()
        
        result = await test_session.get(MealPlan, meal_plan.meal_plan_id)
        assert result is not None
        assert result.user_id == user_in_db.user_id
        assert result.duration == "weekly"
    
    @pytest.mark.asyncio
    async def test_meal_plan_json_content(self, test_session, user_in_db):
        """Test meal plan with complex JSON content."""
        plan_content = {
            "monday": [
                {"meal": "Jollof Rice", "type": "lunch"},
                {"meal": "Pepper Soup", "type": "dinner"}
            ],
            "tuesday": [
                {"meal": "Egusi Soup", "type": "lunch"},
            ]
        }
        
        meal_plan = MealPlan(
            user_id=user_in_db.user_id,
            duration="weekly",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
            plan_content=plan_content
        )
        test_session.add(meal_plan)
        await test_session.commit()
        
        result = await test_session.get(MealPlan, meal_plan.meal_plan_id)
        assert result.plan_content == plan_content


class TestPlanMealModel:
    """Test PlanMeal model."""
    
    @pytest.mark.asyncio
    async def test_create_plan_meal(self, test_session, user_with_meal_plan):
        """Test creating a meal within a plan."""
        user, meal_plan = user_with_meal_plan
        
        plan_meal = PlanMeal(
            meal_plan_id=meal_plan.meal_plan_id,
            meal_name="Jollof Rice",
            meal_type="lunch",
            day_order=1,
            description="Delicious Nigerian Jollof Rice",
            estimated_cook_time=45
        )
        test_session.add(plan_meal)
        await test_session.commit()
        
        result = await test_session.get(PlanMeal, plan_meal.plan_meal_id)
        assert result.meal_name == "Jollof Rice"
        assert result.meal_type == "lunch"
        assert result.selected is False


class TestPlanMealIngredientModel:
    """Test PlanMealIngredient model."""
    
    @pytest.mark.asyncio
    async def test_create_ingredient(self, test_session, user_with_meal_plan):
        """Test creating an ingredient for a meal."""
        user, meal_plan = user_with_meal_plan
        
        # Create a plan meal first
        plan_meal = PlanMeal(
            meal_plan_id=meal_plan.meal_plan_id,
            meal_name="Jollof Rice",
            meal_type="lunch",
            day_order=1
        )
        test_session.add(plan_meal)
        await test_session.commit()
        
        # Create ingredient
        ingredient = PlanMealIngredient(
            plan_meal_id=plan_meal.plan_meal_id,
            ingredient_name="Rice",
            quantity=2,
            unit="cups",
            mapped_product_id="prod_rice_001",
            product_name="Parboiled Rice",
            product_price=18000,
            availability_status="available"
        )
        test_session.add(ingredient)
        await test_session.commit()
        
        result = await test_session.get(PlanMealIngredient, ingredient.ingredient_id)
        assert result.ingredient_name == "Rice"
        assert result.product_price == 18000


class TestPurchaseHistoryModel:
    """Test PurchaseHistory model."""
    
    @pytest.mark.asyncio
    async def test_create_purchase(self, test_session, user_in_db):
        """Test creating a purchase record."""
        purchase = PurchaseHistory(
            user_id=user_in_db.user_id,
            product_id="prod_chicken_001",
            product_name="Fresh Chicken",
            quantity=2,
            unit="kg",
            price=45000,
            ingredient_category="proteins"
        )
        test_session.add(purchase)
        await test_session.commit()
        
        result = await test_session.get(PurchaseHistory, purchase.purchase_id)
        assert result.product_id == "prod_chicken_001"
        assert result.price == 45000


class TestMealFeedbackModel:
    """Test MealFeedback model."""
    
    @pytest.mark.asyncio
    async def test_create_feedback(self, test_session, user_in_db):
        """Test creating feedback."""
        feedback = MealFeedback(
            user_id=user_in_db.user_id,
            meal_viewed=True,
            meal_selected=True,
            user_rating=5
        )
        test_session.add(feedback)
        await test_session.commit()
        
        result = await test_session.get(MealFeedback, feedback.feedback_id)
        assert result.user_rating == 5
        assert result.meal_selected is True


class TestIngredientModel:
    """Test Ingredient model."""
    
    @pytest.mark.asyncio
    async def test_create_ingredient_catalog(self, test_session):
        """Test creating ingredient catalog entry."""
        ingredient = Ingredient(
            name="Chicken",
            category="proteins",
            nigerian_names="Kuku",
            calories=165,
            protein_g=31,
            fat_g=3.6,
            default_unit="kg"
        )
        test_session.add(ingredient)
        await test_session.commit()
        
        result = await test_session.get(Ingredient, ingredient.ingredient_id)
        assert result.name == "Chicken"
        assert result.category == "proteins"


class TestMealTemplateModel:
    """Test MealTemplate model."""
    
    @pytest.mark.asyncio
    async def test_create_meal_template(self, test_session):
        """Test creating a meal template."""
        template = MealTemplate(
            meal_name="Jollof Rice",
            cuisine_type="nigerian",
            difficulty_level="medium",
            estimated_cook_time=45,
            calories=450,
            protein_g=8,
            base_ingredients={
                "rice": {"quantity": 2, "unit": "cups"},
                "tomato": {"quantity": 3, "unit": "pieces"}
            },
            is_vegetarian=False,
            popularity_score=9.5
        )
        test_session.add(template)
        await test_session.commit()
        
        result = await test_session.get(MealTemplate, template.template_id)
        assert result.meal_name == "Jollof Rice"
        assert result.popularity_score == 9.5


class TestModelRelationships:
    """Test model relationships and foreign keys."""
    
    @pytest.mark.asyncio
    async def test_user_meal_plans_relationship(self, test_session, user_with_meal_plan):
        """Test user has many meal plans."""
        user, meal_plan = user_with_meal_plan
        
        # Add another meal plan
        meal_plan2 = MealPlan(
            user_id=user.user_id,
            duration="monthly",
            start_date=datetime.utcnow() + timedelta(days=7),
            end_date=datetime.utcnow() + timedelta(days=37),
            plan_content={}
        )
        test_session.add(meal_plan2)
        await test_session.commit()
        
        # Verify relationship
        result = await test_session.get(User, user.user_id)
        assert len(result.meal_plans) == 2
    
    @pytest.mark.asyncio
    async def test_meal_plan_meals_relationship(self, test_session, user_with_meal_plan):
        """Test meal plan has many meals."""
        user, meal_plan = user_with_meal_plan
        
        # Add multiple meals to plan
        for day in range(1, 8):
            meal = PlanMeal(
                meal_plan_id=meal_plan.meal_plan_id,
                meal_name=f"Meal Day {day}",
                meal_type="lunch",
                day_order=day
            )
            test_session.add(meal)
        
        await test_session.commit()
        
        result = await test_session.get(MealPlan, meal_plan.meal_plan_id)
        assert len(result.meals) >= 2
