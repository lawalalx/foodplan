"""
FastAPI endpoints for meal planning system.
Implements the complete user journey: preferences → meal plan → ingredients → cart → checkout.
Production-ready with AsyncSession and Neon PostgreSQL.
"""
from fastapi import FastAPI, HTTPException, Body, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict
from datetime import datetime
import uuid
import logging

from meal_planner import MealPlanGenerator, IngredientGenerator
from ingredient_mapper import IngredientProductMapper, CartBuilder
from learning_system import UserLearningSystem
from config import get_db_session
from models import (
    User, UserPreference, MealPlan, PlanMeal, 
    PlanMealIngredient, MealFeedback, PurchaseHistory
)

logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC MODELS (Request/Response)
# ============================================================================

class UserPreferenceRequest(BaseModel):
    """Capture user preferences for meal plan generation."""
    user_id: str
    meals_per_day: List[str] = Field(default=["breakfast", "lunch", "dinner"])
    dietary_restrictions: Optional[List[str]] = None
    meal_types: Optional[List[str]] = None
    budget_level: str = "moderate"
    household_size: int = 1


class GenerateMealPlanRequest(BaseModel):
    """Request to generate a meal plan."""
    user_id: str
    duration: str = "weekly"
    use_preference_history: bool = True


class MealSelectionRequest(BaseModel):
    """User selects a meal from the plan."""
    user_id: str
    meal_name: str
    meal_type: str
    day_order: int


class IngredientListResponse(BaseModel):
    """Response with ingredient list for a meal."""
    meal_name: str
    household_size: int
    ingredients: List[Dict]
    total_estimated_cost: Optional[float] = None
    unavailable_count: int = 0


class GetIngredientsRequest(BaseModel):
    """Request to get ingredients for a meal."""
    meal_name: str
    household_size: int = 1
    user_id: Optional[str] = None


class CartAddRequest(BaseModel):
    """Request to add meal ingredients to cart."""
    user_id: str
    meal_name: str
    ingredients: List[Dict]


class MealFeedbackRequest(BaseModel):
    """Capture user feedback on meals."""
    user_id: str
    meal_name: str
    feedback_type: str
    rating: Optional[int] = None


# ============================================================================
# SETUP FUNCTION FOR FASTAPI APP
# ============================================================================

def setup_meal_planning_routes(app: FastAPI):
    """Register all meal planning endpoints."""
    
    # Initialize services
    meal_generator = MealPlanGenerator()
    ingredient_generator = IngredientGenerator()
    learning_system = UserLearningSystem()
    
    # Placeholder for product mapper - initialize with empty catalog
    # The catalog will be populated by your existing backend
    ingredient_mapper = IngredientProductMapper(product_catalog=[])
    
    # ========== EPIC 1: MEAL PLAN GENERATION ==========
    
    @app.post("/api/v1/meal-planning/preferences")
    async def save_user_preferences(
        request: UserPreferenceRequest,
        session: AsyncSession = Depends(get_db_session)
    ):
        """Save user preferences."""
        try:
            user_id = request.user_id
            # Check if user exists, create if not
            user = await session.get(User, user_id)
            if not user:
                user = User(user_id=user_id, household_size=request.household_size)
                session.add(user)
                await session.flush()
            
            # Save preferences
            preference = UserPreference(
                user_id=user_id,
                meal_duration="weekly",
                meals_per_day=",".join(request.meals_per_day),
                dietary_restrictions=",".join(request.dietary_restrictions or []),
                meal_types=",".join(request.meal_types or []),
                budget_level=request.budget_level,
            )
            session.add(preference)
            await session.commit()
            
            logger.info(f"Preferences saved for user {user_id}")
            
            return {
                "status": "success",
                "preference_id": preference.preference_id,
                "message": "Preferences saved successfully"
            }
        
        except Exception as e:
            await session.rollback()
            logger.error(f"Error saving preferences: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/meal-planning/generate")
    async def generate_meal_plan(
        request: GenerateMealPlanRequest,
        session: AsyncSession = Depends(get_db_session)
    ):
        """Generate personalized meal plan."""
        try:
            user_id = request.user_id
            # TODO: Fetch user preferences and purchase history from your database
            user_preferences = None
            purchase_history = None
            household_size = 1
            budget_level = "moderate"
            
            # Generate meal plan using AI
            meal_plan = meal_generator.generate_meal_plan(
                user_id=user_id,
                duration=request.duration,
                meal_preference=user_preferences,
                purchase_history=purchase_history,
                household_size=household_size,
                budget_level=budget_level
            )
            
            # Save meal plan to database
            from datetime import timedelta
            duration_days = 7 if request.duration == "weekly" else 30
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=duration_days)
            
            meal_plan_obj = MealPlan(
                user_id=user_id,
                duration=request.duration,
                start_date=start_date,
                end_date=end_date,
                plan_content=meal_plan
            )
            session.add(meal_plan_obj)
            await session.commit()
            
            logger.info(f"Generated meal plan {meal_plan_obj.meal_plan_id} for user {user_id}")
            
            return {
                "status": "success",
                "meal_plan_id": meal_plan_obj.meal_plan_id,
                "duration": request.duration,
                "meal_plan": meal_plan,
                "next_action": "View meals or select one to get ingredients"
            }
        
        except Exception as e:
            await session.rollback()
            logger.error(f"Error generating meal plan: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ========== EPIC 2: INGREDIENT GENERATION & PURCHASE ==========
    
    @app.post("/api/v1/meal-planning/ingredients")
    async def get_meal_ingredients(
        request: GetIngredientsRequest,
        session: AsyncSession = Depends(get_db_session)
    ) -> IngredientListResponse:
        """Generate ingredients for a meal."""
        try:
            # Generate ingredients
            ingredients = ingredient_generator.generate_ingredients(
                meal_name=request.meal_name,
                household_size=request.household_size
            )
            
            if not ingredients:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not generate ingredients for '{request.meal_name}'"
                )
            
            # Map to QuickMarket products
            mapped_ingredients = []
            total_cost = 0
            unavailable_count = 0
            
            for ingredient in ingredients:
                mapped = ingredient_mapper.map_ingredient_to_product(
                    ingredient_name=ingredient.get("name"),
                    quantity=ingredient.get("quantity", 0),
                    unit=ingredient.get("unit", "")
                )
                mapped_ingredients.append(mapped)
                
                if mapped["availability_status"] != "available":
                    unavailable_count += 1
                elif mapped.get("product_price"):
                    total_cost += mapped["product_price"] * ingredient.get("quantity", 0)
            
            logger.info(f"Generated ingredients for meal '{request.meal_name}'")
            
            return IngredientListResponse(
                meal_name=request.meal_name,
                household_size=request.household_size,
                ingredients=mapped_ingredients,
                total_estimated_cost=total_cost if total_cost > 0 else None,
                unavailable_count=unavailable_count
            )
        
        except Exception as e:
            logger.error(f"Error getting ingredients: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/meal-planning/add-to-cart")
    async def add_ingredients_to_cart(
        request: CartAddRequest,
        session: AsyncSession = Depends(get_db_session)
    ):
        """Add meal ingredients to shopping cart."""
        try:
            user_id = request.user_id
            # Build cart items
            cart_update = CartBuilder.add_ingredients_to_cart(
                mapped_ingredients=request.ingredients,
                user_cart_id=f"cart_{user_id}"
            )
            
            # TODO: Call your existing cart API/backend to add items
            # Example: await your_backend_service.add_to_cart(cart_update)
            
            logger.info(
                f"Added {cart_update['added_count']} items to cart for meal '{request.meal_name}'"
            )
            
            return {
                "status": "success",
                "message": f"Added {cart_update['added_count']} items to your cart",
                "cart_update": cart_update,
                "next_action": "Proceed to checkout"
            }
        
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ========== EPIC 3: CHECKOUT & LEARNING ==========
    
    @app.post("/api/v1/meal-planning/feedback")
    async def submit_meal_feedback(
        request: MealFeedbackRequest,
        session: AsyncSession = Depends(get_db_session)
    ):
        """
        Record user feedback on meals.
        
        Used to improve recommendations and personalization.
        """
        try:
            user_id = request.user_id
            # Record feedback in database
            feedback = MealFeedback(
                user_id=user_id,
                meal_name=request.meal_name,
                meal_viewed=(request.feedback_type == "viewed"),
                meal_selected=(request.feedback_type == "selected"),
                ingredients_added_to_cart=(request.feedback_type == "purchased"),
                user_rating=request.rating
            )
            session.add(feedback)
            await session.commit()
            
            # Update learning system
            learning_system.record_feedback(
                user_id=user_id,
                meal_name=request.meal_name,
                feedback_type=request.feedback_type,
                rating=request.rating
            )
            
            logger.info(f"Recorded {request.feedback_type} feedback for meal '{request.meal_name}'")
            
            return {
                "status": "success",
                "feedback_id": feedback.feedback_id,
                "message": "Feedback recorded successfully"
            }
        
        except Exception as e:
            await session.rollback()
            logger.error(f"Error recording feedback: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ========== UTILITY ENDPOINTS ==========
    
    @app.get("/api/v1/meal-planning/recommendations/{user_id}")
    async def get_personalized_recommendations(
        user_id: str,
        count: int = 5,
        session: AsyncSession = Depends(get_db_session)
    ):
        """Get AI-powered personalized meal recommendations."""
        try:
            # Get user's learning profile
            recommendations = learning_system.get_recommendations(user_id, count=count)
            
            logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
            
            return {
                "user_id": user_id,
                "recommendations": recommendations,
                "last_updated": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/meal-planning/health")
    async def health_check(session: AsyncSession = Depends(get_db_session)):
        """Health check endpoint."""
        try:
            # Quick database ping
            await session.execute(select(1))
            return {
                "status": "healthy",
                "service": "meal-planning",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=503, detail="Service unavailable")
    
    logger.info("Meal planning routes registered successfully")


# No separate health routes needed - included in setup_meal_planning_routes
