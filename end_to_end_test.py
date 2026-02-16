"""
End-to-end test demonstrating the complete meal planning workflow.

WORKFLOW:
1. User enters preferences (or system loads purchase history)
2. AI generates meal plan
3. User selects a meal
4. System generates ingredients
5. Ingredients mapped to QuickMarket products
6. User adds to cart
7. System records feedback for personalization
"""
import uuid
import json
from datetime import datetime
from typing import List, Dict

from meal_planner import MealPlanGenerator, IngredientGenerator
from ingredient_mapper import IngredientProductMapper, CartBuilder
from learning_system import UserLearningSystem


def create_mock_product_catalog() -> List[Dict]:
    """Create mock QuickMarket product catalog for testing."""
    return [
        # Grains
        {"id": "prod_001", "name": "Long Grain Rice (5kg)", "category": "grains", "price": 3500, "availability_status": "available"},
        {"id": "prod_002", "name": "Parboiled Rice (2kg)", "category": "grains", "price": 2500, "availability_status": "available"},
        
        # Proteins
        {"id": "prod_003", "name": "Fresh Chicken (1kg)", "category": "proteins", "price": 5500, "availability_status": "available"},
        {"id": "prod_004", "name": "Beef Cuts (1kg)", "category": "proteins", "price": 6500, "availability_status": "available"},
        {"id": "prod_005", "name": "Frozen Fish (1kg)", "category": "proteins", "price": 4500, "availability_status": "available"},
        
        # Legumes
        {"id": "prod_006", "name": "Black-eyed Beans (2kg)", "category": "legumes", "price": 3000, "availability_status": "available"},
        
        # Vegetables
        {"id": "prod_007", "name": "Fresh Tomato (6 pieces)", "category": "vegetables", "price": 1200, "availability_status": "available"},
        {"id": "prod_008", "name": "Onion (1kg)", "category": "vegetables", "price": 800, "availability_status": "available"},
        {"id": "prod_009", "name": "Fresh Pepper (250g)", "category": "vegetables", "price": 1500, "availability_status": "available"},
        
        # Oils & Seasonings
        {"id": "prod_010", "name": "Palm Oil (1L)", "category": "oils", "price": 2500, "availability_status": "available"},
        {"id": "prod_011", "name": "Vegetable Oil (1L)", "category": "oils", "price": 2000, "availability_status": "available"},
        {"id": "prod_012", "name": "Tomato Paste (400g tin)", "category": "seasonings", "price": 800, "availability_status": "available"},
        {"id": "prod_013", "name": "Egusi Seeds (500g)", "category": "seasonings", "price": 2000, "availability_status": "available"},
    ]


class MealPlanningDemo:
    """
    End-to-end demonstration of the meal planning system.
    Simulates both new user and returning user workflows.
    """
    
    def __init__(self):
        """Initialize demo with required services."""
        self.meal_generator = MealPlanGenerator()
        self.ingredient_generator = IngredientGenerator()
        self.ingredient_mapper = IngredientProductMapper(
            product_catalog=create_mock_product_catalog()
        )
        self.learning_system = UserLearningSystem()
    
    def demo_new_user_workflow(self):
        """Demonstrate workflow for a new user (preference-based)."""
        print("\n" + "="*80)
        print("DEMO: NEW USER WORKFLOW (Preference-Based)")
        print("="*80)
        
        user_id = f"user_{uuid.uuid4()}"
        print(f"\n✓ New user created: {user_id}")
        
        # STEP 1: Capture preferences
        print("\n[STEP 1] Capturing user preferences...")
        preferences = {
            "meals_per_day": ["breakfast", "lunch", "dinner"],
            "dietary_restrictions": ["none"],
            "meal_types": ["nigerian", "international"],
            "budget_level": "moderate"
        }
        household_size = 3
        print(f"  - Household size: {household_size} people")
        print(f"  - Budget: {preferences['budget_level']}")
        print(f"  - Meal types: {', '.join(preferences['meal_types'])}")
        
        # STEP 2: Generate meal plan
        print("\n[STEP 2] Generating weekly meal plan...")
        meal_plan = self.meal_generator.generate_meal_plan(
            user_id=user_id,
            duration="weekly",
            meal_preference=preferences,
            purchase_history=None,
            household_size=household_size,
            budget_level=preferences["budget_level"]
        )
        meal_plan_id = f"plan_{uuid.uuid4()}"
        print(f"✓ Meal plan generated: {meal_plan_id}")
        print("\nSample from meal plan:")
        if "day_1" in meal_plan:
            print(f"  Day 1 (Monday):")
            for meal_type, meal_name in meal_plan["day_1"].items():
                print(f"    - {meal_type.capitalize()}: {meal_name}")
        
        # STEP 3: User selects a meal and feedback
        selected_meal = "Egusi Soup"
        print(f"\n[STEP 3] User views and selects meal: {selected_meal}")
        self.learning_system.record_feedback(
            user_id=user_id,
            meal_name=selected_meal,
            feedback_type="viewed"
        )
        self.learning_system.record_feedback(
            user_id=user_id,
            meal_name=selected_meal,
            feedback_type="selected"
        )
        print(f"✓ Recorded feedback: viewed, selected")
        
        # STEP 4: Generate ingredients
        print(f"\n[STEP 4] Generating ingredients for '{selected_meal}'...")
        ingredients = self.ingredient_generator.generate_ingredients(
            meal_name=selected_meal,
            household_size=household_size
        )
        print(f"✓ Generated {len(ingredients)} ingredients")
        for ing in ingredients[:3]:
            print(f"  - {ing['name']}: {ing['quantity']}{ing['unit']}")
        
        # STEP 5: Map ingredients to products
        print(f"\n[STEP 5] Mapping ingredients to QuickMarket products...")
        mapped_ingredients = []
        for ingredient in ingredients:
            mapped = self.ingredient_mapper.map_ingredient_to_product(
                ingredient_name=ingredient.get("name"),
                quantity=ingredient.get("quantity", 0),
                unit=ingredient.get("unit", "")
            )
            mapped_ingredients.append(mapped)
        
        available = sum(1 for ing in mapped_ingredients if ing["availability_status"] == "available")
        print(f"✓ Mapped {available}/{len(mapped_ingredients)} ingredients to products")
        for ing in mapped_ingredients[:3]:
            status = "✓" if ing["availability_status"] == "available" else "✗"
            print(f"  {status} {ing['ingredient_name']} → {ing['product_name']} (₦{ing['product_price']})")
        
        # STEP 6: Add to cart
        print(f"\n[STEP 6] Adding ingredients to cart...")
        cart_update = CartBuilder.add_ingredients_to_cart(
            mapped_ingredients=mapped_ingredients,
            user_cart_id=f"cart_{user_id}"
        )
        print(f"✓ Added {cart_update['added_count']} items to cart")
        print(f"  Total estimated cost: ₦{cart_update['total_amount']}")
        
        # STEP 7: Record purchase feedback
        print(f"\n[STEP 7] Recording purchase feedback...")
        self.learning_system.record_feedback(
            user_id=user_id,
            meal_name=selected_meal,
            feedback_type="purchased",
            ingredients=[ing["ingredient_name"] for ing in ingredients]
        )
        print(f"✓ Recorded purchase signal for learning")
        
        print("\n✓ NEW USER WORKFLOW COMPLETE")
        return user_id
    
    def demo_returning_user_workflow(self, user_id: str):
        """Demonstrate workflow for returning user (history-based)."""
        print("\n" + "="*80)
        print("DEMO: RETURNING USER WORKFLOW (History-Based)")
        print("="*80)
        
        print(f"\n✓ Returning user: {user_id}")
        
        # Simulate purchase history
        print("\n[STEP 1] Loading user purchase history...")
        purchase_history = [
            {"product_name": "Rice", "category": "grains"},
            {"product_name": "Beans", "category": "legumes"},
            {"product_name": "Chicken", "category": "proteins"},
            {"product_name": "Tomato Paste", "category": "seasonings"},
            {"product_name": "Palm Oil", "category": "oils"},
        ]
        print(f"✓ Loaded {len(purchase_history)} past purchases")
        
        # STEP 2: Generate personalized meal plan
        print("\n[STEP 2] Generating personalized meal plan...")
        meal_plan = self.meal_generator.generate_meal_plan(
            user_id=user_id,
            duration="weekly",
            meal_preference=None,  # Will use history instead
            purchase_history=purchase_history,
            household_size=2,
            budget_level="moderate"
        )
        print(f"✓ Generated personalized meal plan")
        
        # STEP 3: Get recommendations
        print("\n[STEP 3] Getting AI recommendations...")
        recommendations = self.learning_system.get_recommendations(
            user_id=user_id,
            count=3,
            use_history=True
        )
        print(f"✓ Generated {len(recommendations)} recommendations")
        for rec in recommendations:
            print(f"  - {rec['meal_name']}")
        
        # STEP 4: User interactions (simulated)
        print("\n[STEP 4] Simulating user interactions...")
        test_meals = ["Jollof Rice & Stew", "Rice & Beans", "Fried Rice"]
        for meal in test_meals:
            self.learning_system.record_feedback(
                user_id=user_id,
                meal_name=meal,
                feedback_type="viewed"
            )
            if meal != "Rice & Beans":  # User selects 2 out of 3
                self.learning_system.record_feedback(
                    user_id=user_id,
                    meal_name=meal,
                    feedback_type="selected"
                )
        print(f"✓ Recorded interactions for {len(test_meals)} meals")
        
        # STEP 5: Get user insights
        print("\n[STEP 5] Analyzing user behavior...")
        insights = self.learning_system.get_user_insights(user_id)
        print(f"✓ User insights:")
        print(f"  - Total interactions: {insights['total_interactions']}")
        print(f"  - Average rating: {insights['average_rating']}")
        
        print("\n✓ RETURNING USER WORKFLOW COMPLETE")
    
    def demo_ingredient_removal_learning(self, user_id: str):
        """Demonstrate how ingredient removals improve personalization."""
        print("\n" + "="*80)
        print("DEMO: INGREDIENT REMOVAL & PREFERENCE LEARNING")
        print("="*80)
        
        print(f"\nUser {user_id} removes certain ingredients:")
        
        # Simulate ingredient removals (e.g., allergies, preferences)
        removed_ingredients = ["Crayfish", "Palm Oil", "Pepper"]
        for ingredient in removed_ingredients:
            self.learning_system.record_ingredient_removal(
                user_id=user_id,
                meal_name="Egusi Soup",
                ingredient_name=ingredient
            )
            print(f"  ✓ Removed: {ingredient}")
        
        print("\n✓ System will use this data to:")
        print("  - Suggest alternatives for future meal plans")
        print("  - Avoid these ingredients in similar meals")
        print("  - Identify possible dietary restrictions")
        print("  - Improve personalization")


def run_complete_demo():
    """Run the complete end-to-end demonstration."""
    print("\n" + "="*80)
    print("MEAL PLANNING SYSTEM - END-TO-END DEMONSTRATION")
    print("="*80)
    print("\nThis demo shows the complete workflow from preferences to checkout,")
    print("for both new and returning users.")
    
    demo = MealPlanningDemo()
    
    # Demo 1: New user
    user_id = demo.demo_new_user_workflow()
    
    # Demo 2: Same user as returning (after initial signup)
    demo.demo_returning_user_workflow(user_id)
    
    # Demo 3: Learning from interactions
    demo.demo_ingredient_removal_learning(user_id)
    
    print("\n" + "="*80)
    print("DEMO COMPLETE")
    print("="*80)
    print("\nKEY FEATURES DEMONSTRATED:")
    print("✓ Preference capture (new users)")
    print("✓ Meal plan generation (AI-powered)")
    print("✓ Ingredient generation with portions")
    print("✓ Product mapping to QuickMarket catalog")
    print("✓ Cart integration")
    print("✓ Feedback recording for learning")
    print("✓ Personalized recommendations (returning users)")
    print("✓ User behavior analytics")
    print("✓ Ingredient removal tracking")
    print("\nNEXT STEPS:")
    print("1. Connect to actual database (SQLAlchemy + ORM)")
    print("2. Integrate with real QuickMarket product catalog")
    print("3. Deploy API endpoints")
    print("4. Set up meal template database")
    print("5. Implement advanced recommendation algorithms")


if __name__ == "__main__":
    run_complete_demo()
