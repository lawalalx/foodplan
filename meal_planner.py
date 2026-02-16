"""
AI-powered meal plan generation using LLM.
Handles both preference-based (new users) and history-based (returning users) generation.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class MealPlanGenerator:
    """Generate personalized meal plans using AI."""
    
    def __init__(self):
        """Initialize the meal plan generator with LLM."""
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            api_key=os.environ.get("GROQ_API_KEY")
        )
    
    def generate_meal_plan(
        self,
        user_id: str,
        duration: str = "weekly",  # "weekly" or "monthly"
        meal_preference: Optional[Dict] = None,
        purchase_history: Optional[List[Dict]] = None,
        household_size: int = 1,
        budget_level: str = "moderate"
    ) -> Dict:
        """
        Generate a meal plan for a user.
        
        Args:
            user_id: User identifier
            duration: "weekly" or "monthly"
            meal_preference: Dict with dietary preferences (from new users)
            purchase_history: List of past purchases (from returning users)
            household_size: Number of people to cook for
            budget_level: "budget-friendly", "moderate", or "premium"
            
        Returns:
            Dict with meal plan structure {day: [meals]}
        """
        # Build user context
        context = self._build_user_context(
            meal_preference, purchase_history, household_size, budget_level
        )
        
        # Create prompt
        prompt = self._create_meal_plan_prompt(duration, context)
        
        # Call LLM
        try:
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=prompt)
            ]
            response = self.llm.invoke(messages)
            
            # Parse response
            meal_plan = self._parse_meal_plan_response(response.content, duration)
            
            logger.info(f"Generated meal plan for user {user_id}: {duration}")
            return meal_plan
            
        except Exception as e:
            logger.error(f"Error generating meal plan: {e}")
            raise
    
    def _build_user_context(
        self,
        meal_preference: Optional[Dict],
        purchase_history: Optional[List[Dict]],
        household_size: int,
        budget_level: str
    ) -> str:
        """Build context string from user preferences and history."""
        context_parts = [f"Household size: {household_size} people"]
        context_parts.append(f"Budget level: {budget_level}")
        
        if meal_preference:
            if meal_preference.get("meals_per_day"):
                context_parts.append(f"Meals per day: {meal_preference['meals_per_day']}")
            if meal_preference.get("dietary_restrictions"):
                context_parts.append(f"Dietary restrictions: {meal_preference['dietary_restrictions']}")
            if meal_preference.get("meal_types"):
                context_parts.append(f"Preferred meal types: {meal_preference['meal_types']}")
        
        if purchase_history:
            # Extract frequently bought ingredients
            ingredient_counts = {}
            for purchase in purchase_history[-20:]:  # Last 20 purchases
                ingredient = purchase.get("product_name", "")
                ingredient_counts[ingredient] = ingredient_counts.get(ingredient, 0) + 1
            
            top_ingredients = sorted(
                ingredient_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]
            top_names = [name for name, count in top_ingredients]
            context_parts.append(f"Frequently bought: {', '.join(top_names)}")
        
        return "\n".join(context_parts)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for meal plan generation."""
        return """You are a meal planning AI specialist for QuickMarket, a Nigerian grocery delivery service.
Your role is to generate personalized weekly or monthly meal plans for users.

GUIDELINES:
1. Focus on Nigerian and African cuisine with international options
2. Ensure nutritional balance: proteins, vegetables, grains, healthy fats
3. Consider user preferences, budget, and household size
4. Meals should be practical and cookable by average home cooks
5. Vary meals to reduce monotony
6. For budget-friendly plans: suggest beans, rice, eggs, local vegetables
7. For moderate/premium: include more proteins (fish, meat) and variety
8. Always include breakfast, lunch, and dinner (or as requested)
9. Return ONLY valid JSON format

POPULAR NIGERIAN MEALS TO INCLUDE:
- Jollof rice, fried rice, coconut rice
- Egusi soup, okra soup, pepper soup
- Beans, garri, eba, swallow
- Suya, moi moi, akara
- Stew (tomato, pepper), curry
- Grilled fish, pepper soup
"""
    
    def _create_meal_plan_prompt(self, duration: str, context: str) -> str:
        """Create the prompt for meal plan generation."""
        days = 7 if duration == "weekly" else 30
        
        return f"""Generate a {duration} meal plan for {days} days.

USER CONTEXT:
{context}

REQUIREMENTS:
1. Return ONLY valid JSON (no markdown, no explanations)
2. Format:
{{
  "meal_plan": {{
    "day_1": {{
      "breakfast": "Pap & Akara",
      "lunch": "Egusi Soup & Swallow",
      "dinner": "Jollof Rice & Stew"
    }},
    "day_2": {{ ... }}
  }},
  "summary": {{
    "total_days": {days},
    "nutritional_focus": "balanced with protein emphasis",
    "budget_estimate": "₦X,XXX per day",
    "prep_tips": ["tip1", "tip2"]
  }}
}}

3. Each day must have breakfast, lunch, dinner
4. Meals should be varied and practical
5. Include at least 3 Nigerian meals per week
6. Consider dietary restrictions mentioned in context
7. Meals should be suitable for the stated household size
8. Budget-friendly means using affordable proteins (beans, eggs) and local vegetables

Generate the meal plan now:"""
    
    def _parse_meal_plan_response(self, response: str, duration: str) -> Dict:
        """Parse the LLM response into a structured meal plan."""
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            # Extract meal plan
            meal_plan = data.get("meal_plan", {})
            
            # Standardize format if needed
            if not meal_plan:
                meal_plan = data
            
            return meal_plan
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse meal plan JSON: {e}")
            logger.error(f"Response: {response[:500]}")
            # Return a basic fallback structure
            return {
                "day_1": {
                    "breakfast": "Pap & Akara",
                    "lunch": "Rice & Beans",
                    "dinner": "Jollof Rice & Stew"
                }
            }


class IngredientGenerator:
    """Generate ingredient lists for meals with portion adjustments."""
    
    def __init__(self):
        """Initialize the ingredient generator."""
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            api_key=os.environ.get("GROQ_API_KEY")
        )
        # Load ingredient templates
        self.ingredient_database = self._load_ingredient_templates()
    
    def generate_ingredients(
        self,
        meal_name: str,
        household_size: int = 1,
        servings: int = 1
    ) -> List[Dict]:
        """
        Generate ingredient list for a meal with adjusted quantities.
        
        Args:
            meal_name: Name of the meal
            household_size: Number of people
            servings: Number of servings needed
            
        Returns:
            List of ingredients with quantities
        """
        prompt = f"""Generate a detailed ingredient list for "{meal_name}".

REQUIREMENTS:
1. Return ONLY valid JSON (no markdown)
2. Adjust portions for {household_size} people, {servings} serving(s)
3. Include quantities in practical units (kg, cups, tablespoons, pieces, etc.)
4. Return format:
[
  {{"name": "ingredient name", "quantity": 500, "unit": "g", "notes": "optional notes"}},
  {{"name": "ingredient name", "quantity": 2, "unit": "cups", "notes": "optional notes"}}
]

Generate ingredients for {meal_name}:"""
        
        try:
            messages = [
                SystemMessage(content="You are a Nigerian cooking expert. Generate ingredient lists for meals."),
                HumanMessage(content=prompt)
            ]
            response = self.llm.invoke(messages)
            
            # Parse JSON response
            ingredients = self._parse_ingredients_response(response.content)
            return ingredients
            
        except Exception as e:
            logger.error(f"Error generating ingredients for {meal_name}: {e}")
            return []
    
    def _load_ingredient_templates(self) -> Dict:
        """Load predefined ingredient templates for common meals."""
        return {
            "Egusi Soup": [
                {"name": "Egusi seeds", "quantity": 500, "unit": "g"},
                {"name": "Palm oil", "quantity": 250, "unit": "ml"},
                {"name": "Beef", "quantity": 1, "unit": "kg"},
                {"name": "Stockfish", "quantity": 2, "unit": "pieces"},
                {"name": "Crayfish", "quantity": 100, "unit": "g"},
                {"name": "Pepper", "quantity": 5, "unit": "pieces"},
                {"name": "Salt", "quantity": 1, "unit": "teaspoon"},
            ],
            "Jollof Rice": [
                {"name": "Long grain rice", "quantity": 2, "unit": "cups"},
                {"name": "Tomato paste", "quantity": 3, "unit": "tablespoons"},
                {"name": "Onions", "quantity": 2, "unit": "pieces"},
                {"name": "Bell pepper", "quantity": 1, "unit": "piece"},
                {"name": "Vegetable oil", "quantity": 50, "unit": "ml"},
                {"name": "Pepper", "quantity": 3, "unit": "pieces"},
                {"name": "Chicken stock", "quantity": 1, "unit": "teaspoon"},
            ],
            "Pap & Akara": [
                {"name": "Cornmeal (pap)", "quantity": 2, "unit": "cups"},
                {"name": "Black-eyed beans", "quantity": 2, "unit": "cups"},
                {"name": "Onions", "quantity": 1, "unit": "piece"},
                {"name": "Vegetable oil", "quantity": 500, "unit": "ml"},
                {"name": "Salt", "quantity": 1, "unit": "teaspoon"},
            ]
        }
    
    def _parse_ingredients_response(self, response: str) -> List[Dict]:
        """Parse ingredient list from LLM response."""
        try:
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON array found")
            
            json_str = response[json_start:json_end]
            ingredients = json.loads(json_str)
            
            return ingredients if isinstance(ingredients, list) else []
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse ingredients: {e}")
            return []
