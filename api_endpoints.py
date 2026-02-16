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
    import os
    import httpx
    import asyncio

    # Placeholder for product mapper - initialize with empty catalog
    # The catalog will be populated by your existing backend (see PRODUCT_CATALOG_URL)
    ingredient_mapper = IngredientProductMapper(product_catalog=[])

    PRODUCT_CATALOG_URL = os.environ.get("PRODUCT_CATALOG_URL") or os.environ.get("BACKEND_CATALOG_URL")
    # Background refresh interval (seconds)
    CATALOG_REFRESH_INTERVAL = int(os.environ.get("CATALOG_REFRESH_INTERVAL", "600"))

    async def _catalog_refresher():
        """Background task that periodically refreshes the product catalog."""
        while True:
            try:
                if PRODUCT_CATALOG_URL:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.get(PRODUCT_CATALOG_URL)
                        if resp.status_code == 200:
                            products = resp.json()
                            ingredient_mapper.update_catalog(products)
                            logger.info(f"Catalog refreshed with {len(products)} items")
                        else:
                            logger.debug(f"Catalog refresh returned status {resp.status_code}")
            except asyncio.CancelledError:
                logger.info("Catalog refresher cancelled")
                break
            except Exception as e:
                logger.warning(f"Catalog refresher error: {e}")

            await asyncio.sleep(CATALOG_REFRESH_INTERVAL)

    # Register startup/shutdown handlers to manage the background refresher
    app.add_event_handler(
        "startup",
        lambda: setattr(app.state, "_catalog_task", asyncio.create_task(_catalog_refresher()))
    )

    def _stop_catalog_task():
        task = getattr(app.state, "_catalog_task", None)
        if task:
            task.cancel()

    app.add_event_handler("shutdown", _stop_catalog_task)
    
    # ========== EPIC 1: MEAL PLAN GENERATION ==========
    
    @app.post("/api/v1/meal-planning/preferences")
    async def save_user_preferences(
        request: UserPreferenceRequest,
        session: AsyncSession = Depends(get_db_session)
    ):
        """
        Save user meal preferences and profile.
        
        **Purpose:** Store user's dietary restrictions, budget level, household size, and meal preferences.
        These preferences are used to personalize meal plan generation.
        
        **When to call:** 
        - First time a new user visits the app
        - When user updates their profile/preferences
        - Required before calling /generate for accurate meal plans
        
        **Request Body:**
        - `user_id` (string, required): Unique identifier for the user (e.g., from your auth system)
        - `household_size` (integer, default=1): Number of people to cook for (1-10)
        - `meals_per_day` (array[string], default=["breakfast", "lunch", "dinner"]): Which meals to include in plan
        - `dietary_restrictions` (array[string], optional): e.g., ["no-pork", "no-dairy", "vegetarian"]
        - `meal_types` (array[string], optional): e.g., ["nigerian", "caribbean", "asian"]
        - `budget_level` (string, default="moderate"): "budget-friendly", "moderate", or "premium"
        
        **Response (200 OK):**
        ```json
        {
          "status": "success",
          "preference_id": "pref_uuid_here",
          "message": "Preferences saved successfully"
        }
        ```
        
        **Example Request:**
        ```json
        {
          "user_id": "user_12345",
          "household_size": 4,
          "meals_per_day": ["breakfast", "lunch", "dinner"],
          "dietary_restrictions": ["no-pork"],
          "meal_types": ["nigerian"],
          "budget_level": "moderate"
        }
        ```
        
        **Error Responses:**
        - 400: Invalid data format
        - 500: Database error
        """
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
        """
        Generate an AI-powered personalized meal plan.
        
        **Purpose:** Create a multi-day meal plan tailored to user preferences, dietary restrictions, and budget.
        Uses LLM (AI) to generate creative meal combinations and considers purchase history if available.
        
        **When to call:**
        - After user saves preferences (via /preferences endpoint)
        - When user wants a new meal plan for the week/month
        - Typically called once per week or when user clicks "Get Meal Plan"
        
        **Prerequisites:** User must call /preferences endpoint first
        
        **Request Body:**
        - `user_id` (string, required): User ID (same as saved in /preferences)
        - `duration` (string, default="weekly"): "weekly" (7 days) or "monthly" (30 days)
        - `use_preference_history` (boolean, default=true): Use saved preferences and purchase history for personalization
        
        **Response (200 OK):**
        ```json
        {
          "status": "success",
          "meal_plan_id": "plan_uuid_here",
          "duration": "weekly",
          "meal_plan": {
            "day_1": {
              "breakfast": "Scrambled Eggs & Toast",
              "lunch": "Grilled Chicken & Fried Rice",
              "dinner": "Okra Soup & Eba"
            },
            "day_2": { ... },
            ...
            "day_7": { ... }
          },
          "next_action": "View meals or select one to get ingredients"
        }
        ```
        
        **Response Fields:**
        - `meal_plan_id`: Unique ID for this plan (save for reference)
        - `duration`: "weekly" or "monthly"
        - `meal_plan`: Object with day_1...day_N keys, each containing breakfast/lunch/dinner
        - `next_action`: Hint for what frontend should do next
        
        **Example Request:**
        ```json
        {
          "user_id": "user_12345",
          "duration": "weekly",
          "use_preference_history": true
        }
        ```
        
        **Error Responses:**
        - 400: User not found or preferences not set
        - 500: LLM generation failed or database error
        
        **Frontend Flow:**
        1. Display the meal_plan to user (day-by-day view)
        2. Let user select a meal and call /ingredients to see what to buy
        3. Allow user to add selected meals to cart via /add-to-cart
        """
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
        """
        Get ingredients and products for a selected meal.
        
        **Purpose:** 
        - Generate a detailed shopping list for a specific meal
        - Map ingredient names to real QuickMarket products with prices and availability
        - Provide product IDs needed for adding to cart
        
        **When to call:**
        - User clicks on a meal from the generated plan
        - User wants to see what to buy and the costs
        - Before calling /add-to-cart (use the ingredients from this response)
        
        **Request Body:**
        - `meal_name` (string, required): Name of the meal (e.g., "Jollof Rice") from /generate response
        - `household_size` (integer, default=1): Number of servings/people (adjusts ingredient quantities)
        - `user_id` (string, optional): User ID for tracking
        
        **Response (200 OK):**
        ```json
        {
          "meal_name": "Jollof Rice",
          "household_size": 4,
          "total_estimated_cost": 15000,
          "unavailable_count": 2,
          "ingredients": [
            {
              "ingredient_name": "Long-grain rice",
              "quantity": 2,
              "unit": "kg",
              "mapped_product_id": "prod_rice_001",
              "product_name": "Long Grain Rice 5kg",
              "product_price": 12000,
              "availability_status": "available",
              "substitute_product_id": null,
              "confidence_score": 0.95,
              "notes": "Mapped with 95% confidence"
            },
            {
              "ingredient_name": "Tomato paste",
              "quantity": 200,
              "unit": "g",
              "mapped_product_id": null,
              "product_name": null,
              "product_price": null,
              "availability_status": "unavailable",
              "substitute_product_id": null,
              "confidence_score": 0.0,
              "notes": "No product match found. User can search manually."
            },
            ...
          ]
        }
        ```
        
        **Response Fields:**
        - `meal_name`: The meal you requested ingredients for
        - `household_size`: Number of servings
        - `total_estimated_cost`: Total cost in currency (null if some items unavailable)
        - `unavailable_count`: How many ingredients couldn't be mapped to products
        - `ingredients`: Array of ingredient objects with product mappings
        
        **Ingredient Object Fields:**
        - `ingredient_name`: Original ingredient name (e.g., "Long-grain rice")
        - `quantity` & `unit`: Amount needed (e.g., 2 kg, 1 cup)
        - `mapped_product_id`: QuickMarket product ID (null if not found)
        - `product_name`: Actual product name from QuickMarket (null if not found)
        - `product_price`: Price per unit (null if not found)
        - `availability_status`: "available" | "unavailable" | "substitute"
        - `confidence_score`: How confident the mapping is (0.0-1.0)
        - `substitute_product_id`: Alternative product if main one unavailable
        - `notes`: Explanation of mapping result
        
        **Example Request:**
        ```json
        {
          "meal_name": "Jollof Rice",
          "household_size": 4,
          "user_id": "user_12345"
        }
        ```
        
        **Frontend Tips:**
        1. Display ingredients in a table with product name, quantity, unit price, total
        2. Highlight unavailable items (availability_status != "available") in red
        3. Show confidence score or let user edit/search for better matches
        4. Call /add-to-cart with filtered available ingredients or ask user to approve
        5. Calculate total cost from product_price * quantity
        
        **Error Responses:**
        - 400: Meal not found or couldn't generate ingredients
        - 500: Ingredient generation or mapping error
        """
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
            
            # If mapper has no catalog, try to load it from backend
            if not ingredient_mapper.product_catalog and PRODUCT_CATALOG_URL:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.get(PRODUCT_CATALOG_URL)
                        if resp.status_code == 200:
                            products = resp.json()
                            # Expecting list of products with fields: id, name, category, price, availability_status
                            ingredient_mapper.update_catalog(products)
                            logger.info(f"Loaded product catalog with {len(products)} items from backend")
                        else:
                            logger.warning(f"Failed to load product catalog: {resp.status_code}")
                except Exception as e:
                    logger.warning(f"Error fetching product catalog: {e}")

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

                # If still unmatched and backend supports search, try single-item search fallback
                if (not mapped.get("mapped_product_id") and PRODUCT_CATALOG_URL):
                    try:
                        search_url = PRODUCT_CATALOG_URL.rstrip('/') + "/search"
                        params = {"q": ingredient.get("name")}
                        async with httpx.AsyncClient(timeout=6.0) as client:
                            sresp = await client.get(search_url, params=params)
                            if sresp.status_code == 200:
                                results = sresp.json()
                                if isinstance(results, list) and results:
                                    # Update mapper catalog with these results and remap
                                    ingredient_mapper.update_catalog(results + ingredient_mapper.product_catalog)
                                    mapped = ingredient_mapper.map_ingredient_to_product(
                                        ingredient_name=ingredient.get("name"),
                                        quantity=ingredient.get("quantity", 0),
                                        unit=ingredient.get("unit", "")
                                    )
                    except Exception as se:
                        logger.debug(f"Search fallback failed for '{ingredient.get('name')}': {se}")
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
        """
        Add selected meal ingredients to user's shopping cart.
        
        **Purpose:**
        - Convert meal ingredients into cart items with prices and totals
        - Prepare items for checkout
        - Build a unified shopping cart from multiple meals if desired
        
        **When to call:**
        - After user reviews ingredients from /ingredients endpoint
        - User clicks "Add to Cart" or "Buy Now"
        - Can be called multiple times to add different meals to same cart
        
        **Request Body:**
        - `user_id` (string, required): User ID
        - `meal_name` (string, required): Name of the meal being added
        - `ingredients` (array, required): Mapped ingredient objects from /ingredients response
          (Must include: mapped_product_id, product_name, product_price, quantity, unit)
        
        **Response (200 OK):**
        ```json
        {
          "status": "success",
          "message": "Added 12 items to your cart",
          "cart_update": {
            "user_cart_id": "cart_user_12345",
            "added_count": 12,
            "skipped_count": 2,
            "total_amount": 45000,
            "items": [
              {
                "product_id": "prod_rice_001",
                "product_name": "Long Grain Rice 5kg",
                "quantity": 2,
                "unit": "kg",
                "price": 12000,
                "subtotal": 24000,
                "from_meal_plan": true,
                "meal_ingredient": "Long-grain rice"
              },
              ...
            ],
            "skipped_items": [
              {
                "ingredient": "Tomato paste",
                "reason": "Not available at QuickMarket"
              }
            ]
          },
          "next_action": "Proceed to checkout"
        }
        ```
        
        **Response Fields:**
        - `status`: "success" or "error"
        - `message`: Human-readable summary
        - `cart_update`: Details of items added
          - `user_cart_id`: Unique cart identifier
          - `added_count`: Items successfully added
          - `skipped_count`: Items skipped (unavailable or no mapping)
          - `total_amount`: Total cost in currency
          - `items`: Array of cart items with prices
          - `skipped_items`: Items that couldn't be added with reasons
        - `next_action`: Hint for frontend (should redirect to checkout)
        
        **Example Request:**
        ```json
        {
          "user_id": "user_12345",
          "meal_name": "Jollof Rice",
          "ingredients": [
            {
              "ingredient_name": "Long-grain rice",
              "quantity": 2,
              "unit": "kg",
              "mapped_product_id": "prod_rice_001",
              "product_name": "Long Grain Rice 5kg",
              "product_price": 12000,
              "availability_status": "available",
              "confidence_score": 0.95
            },
            ...
          ]
        }
        ```
        
        **Frontend Flow:**
        1. Get ingredients from /ingredients
        2. User reviews and optionally edits quantities
        3. Send to /add-to-cart with ingredients
        4. Display added_count and total_amount
        5. Show skipped_items if any (ask user if they want to search for alternatives)
        6. Provide "Proceed to Checkout" button that calls your backend cart/checkout API
        
        **Error Responses:**
        - 400: Invalid ingredient data format
        - 500: Cart update error
        
        **Notes:**
        - Only items with mapped_product_id will be added
        - Unavailable items are skipped (but could have substitute_product_id available)
        - Multiple calls to this endpoint accumulate in the cart
        """
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
        Record user feedback on meals for personalization.
        
        **Purpose:**
        - Log user interactions with meals (viewed, selected, purchased)
        - Capture ratings to improve recommendations
        - Train personalization engine to suggest better meals over time
        
        **When to call:**
        - After user views a meal in the plan (feedback_type="viewed")
        - When user selects a meal to cook (feedback_type="selected")
        - After user purchases ingredients (feedback_type="purchased")
        - Optionally when user rates a meal (include rating)
        
        **Request Body:**
        - `user_id` (string, required): User ID
        - `meal_name` (string, required): Name of the meal
        - `feedback_type` (string, required): "viewed" | "selected" | "purchased"
        - `rating` (integer, optional): 1-5 star rating (1=poor, 5=excellent)
        
        **Response (200 OK):**
        ```json
        {
          "status": "success",
          "feedback_id": "feedback_uuid_here",
          "message": "Feedback recorded successfully"
        }
        ```
        
        **Example Requests:**
        
        User viewed a meal:
        ```json
        {
          "user_id": "user_12345",
          "meal_name": "Jollof Rice",
          "feedback_type": "viewed",
          "rating": null
        }
        ```
        
        User purchased and rated:
        ```json
        {
          "user_id": "user_12345",
          "meal_name": "Jollof Rice",
          "feedback_type": "purchased",
          "rating": 5
        }
        ```
        
        **Feedback Types:**
        - `viewed`: User scrolled past or opened the meal details
        - `selected`: User decided to cook this meal
        - `purchased`: User bought ingredients for this meal
        
        **Frontend Tips:**
        1. Auto-track "viewed" when user opens meal details
        2. Send "selected" when user clicks "Cook This" or "Get Ingredients"
        3. Send "purchased" after successful checkout
        4. Offer a 5-star rating modal after purchase (optional)
        5. Don't wait for response; fire-and-forget is fine (async)
        
        **Error Responses:**
        - 400: Invalid feedback_type or missing required fields
        - 500: Database error
        
        **Impact:**
        - Meals with high ratings and "purchased" feedback will rank higher
        - User will get better personalized recommendations in future /generate calls
        - System learns user's taste preferences over time
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
        """
        Get personalized meal recommendations based on user history.
        
        **Purpose:**
        - Return the top meal suggestions for a user
        - Ranked by purchase history, ratings, and preferences
        - Help users quickly find meals they'll love
        
        **When to call:**
        - Display "Recommended for You" section on home/dashboard
        - Suggest meals when user hasn't used the planner yet
        - Refresh recommendations periodically
        
        **Prerequisites:**
        - User should have submitted feedback via /feedback endpoint (optional but improves results)
        - User should have at least one meal plan generated
        
        **URL Parameters:**
        - `user_id` (string, required): User ID (path parameter)
        - `count` (integer, optional, default=5): How many recommendations to return (1-20)
        
        **Query Example:**
        ```
        GET /api/v1/meal-planning/recommendations/user_12345?count=5
        ```
        
        **Response (200 OK):**
        ```json
        {
          "user_id": "user_12345",
          "recommendations": [
            "Jollof Rice",
            "Egusi Soup",
            "Fried Rice",
            "Moi Moi",
            "Pepper Soup"
          ],
          "last_updated": "2026-02-15T10:30:00Z"
        }
        ```
        
        **Response Fields:**
        - `user_id`: The user requested
        - `recommendations`: Array of meal names ranked by relevance (best first)
        - `last_updated`: Timestamp of when recommendations were generated
        
        **How Recommendations are Ranked:**
        1. Meals user has purchased and rated highly (5 stars)
        2. Meals matching user's dietary restrictions and preferences
        3. Meals similar to user's favorites
        4. Popular meals within user's budget level
        5. Diverse meals to encourage variety
        
        **Frontend Tips:**
        1. Display in a carousel or list with "Cook This" buttons
        2. Clicking on a recommendation should fetch /ingredients for that meal
        3. Update recommendations after user gives feedback
        4. Show fallback generic recommendations if user has no history
        
        **Example Usage:**
        ```javascript
        // Ask for 5 personalized recommendations
        const response = await fetch('/api/v1/meal-planning/recommendations/user_12345?count=5');
        const data = await response.json();
        // data.recommendations = ["Jollof Rice", "Egusi Soup", ...]
        ```
        
        **Error Responses:**
        - 404: User not found
        - 500: Recommendation generation error
        
        **Notes:**
        - First call for new users returns popular meals (no history)
        - Improves accuracy as user provides more feedback
        - Use with /feedback to create a feedback loop
        """
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
        """
        Health check / status endpoint.
        
        **Purpose:**
        - Verify the meal planning service is running and healthy
        - Check database connectivity
        - Used for monitoring and load balancer health checks
        
        **When to call:**
        - On app startup (before showing meal planner to user)
        - Periodically for uptime monitoring
        - Before critical operations (optional safeguard)
        
        **URL:**
        ```
        GET /api/v1/meal-planning/health
        ```
        
        **Response (200 OK) - Service Healthy:**
        ```json
        {
          "status": "healthy",
          "service": "meal-planning",
          "timestamp": "2026-02-15T10:30:00Z"
        }
        ```
        
        **Response (503 Service Unavailable) - Service Down:**
        ```json
        {
          "detail": "Service unavailable"
        }
        ```
        
        **Response Fields:**
        - `status`: "healthy" = all systems operational
        - `service`: Name of service ("meal-planning")
        - `timestamp`: ISO 8601 timestamp of health check
        
        **Frontend Tips:**
        1. Call on app load; show loading spinner until healthy
        2. Display error banner if status != 200
        3. Disable meal planner UI if service unhealthy
        4. Log health check failures for debugging
        
        **Monitoring:**
        - Use for Kubernetes/Docker health probes
        - Set timeout to 5-10 seconds
        - Acceptable interval: every 30 seconds
        
        **Example curl:**
        ```bash
        curl -X GET http://localhost:8000/api/v1/meal-planning/health
        ```
        """
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
