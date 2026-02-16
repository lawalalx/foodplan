# {
#   "user_id": "user_12345",
#   "household_size": 4,
#   "meals_per_day": ["breakfast", "lunch", "dinner"],
#   "dietary_restrictions": ["no-pork"],
#   "meal_types": ["nigerian"],
#   "budget_level": "moderate"
# }




# 2. Generate Meal Plan
# POST /api/v1/meal-planning/generate

# Request Body:


# {
#   "user_id": "user_12345",
#   "duration": "weekly",
#   "use_preference_history": true
# }



# 3. Get Ingredients for a Meal
# POST /api/v1/meal-planning/ingredients
# {
#   "meal_name": "Jollof Rice",
#   "household_size": 4,
#   "user_id": "user_12345"
# }


# POST /api/v1/meal-planning/add-to-cart



# 5. Submit Feedback
# POST /api/v1/meal-planning/feedback
# {
#   "user_id": "user_12345",
#   "meal_name": "Jollof Rice",
#   "feedback_type": "viewed",
#   "rating": null
# }


# 6. Get Personalized Recommendations
# GET /api/v1/meal-planning/recommendations/user_12345?count=5
# {
#   "user_id": "user_12345",
#   "recommendations": [
#     "Jollof Rice",
#     "Egusi Soup",
#     "Fried Rice",
#     "Moi Moi",
#     "Pepper Soup"
#   ],
#   "last_updated": "2026-02-15T10:30:00Z"
# }
