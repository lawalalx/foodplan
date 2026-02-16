"""
User learning system for meal plan personalization.
Tracks user behavior and improves recommendations over time.

SIGNALS CAPTURED:
- Meals viewed
- Meals selected
- Ingredients purchased
- Ingredients removed
- Repeat cooking behavior
- User ratings

USES:
- Better personalization
- Smarter meal suggestions
- Cross-selling
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter, defaultdict
import json

logger = logging.getLogger(__name__)


class MealFeedback:
    """Data class for meal feedback."""
    
    def __init__(
        self,
        feedback_id: str,
        user_id: str,
        meal_plan_id: str,
        meal_name: str,
        feedback_type: str,  # "viewed", "selected", "purchased", "cooked"
        user_rating: Optional[int] = None,
        timestamp: Optional[datetime] = None
    ):
        self.feedback_id = feedback_id
        self.user_id = user_id
        self.meal_plan_id = meal_plan_id
        self.meal_name = meal_name
        self.feedback_type = feedback_type
        self.user_rating = user_rating
        self.timestamp = timestamp or datetime.utcnow()


class UserLearningProfile:
    """Tracks learning profile for a user."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        
        # Meal preferences
        self.meal_views = Counter()  # meal_name -> view count
        self.meal_selections = Counter()  # meal_name -> selection count
        self.meal_purchases = Counter()  # meal_name -> purchase count
        self.meal_ratings = {}  # meal_name -> [ratings]
        
        # Ingredient preferences
        self.ingredient_purchases = Counter()  # ingredient -> count
        self.ingredient_removals = Counter()  # ingredient -> removal count
        
        # Temporal patterns
        self.meal_cook_frequency = {}  # meal_name -> cook dates
        self.purchase_frequency_by_day = defaultdict(int)  # day_of_week -> count
        
        # Metadata
        self.created_at = datetime.utcnow()
        self.last_updated = datetime.utcnow()
        self.total_interactions = 0


class UserLearningSystem:
    """
    Main learning system for meal plan personalization.
    Stateless but uses user context for better recommendations.
    """
    
    def __init__(self):
        """Initialize learning system."""
        self.user_profiles = {}  # user_id -> UserLearningProfile
        self.meal_popularity = Counter()  # meal_name -> global popularity
    
    def record_feedback(
        self,
        user_id: str,
        meal_name: str,
        feedback_type: str,
        rating: Optional[int] = None,
        ingredients: Optional[List[str]] = None
    ):
        """
        Record user feedback on a meal.
        
        Args:
            user_id: User identifier
            meal_name: Name of the meal
            feedback_type: "viewed", "selected", "purchased", "cooked"
            rating: Optional 1-5 rating
            ingredients: Optional list of ingredients (for ingredient tracking)
        """
        # Get or create user profile
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserLearningProfile(user_id)
        
        profile = self.user_profiles[user_id]
        
        # Record feedback
        if feedback_type == "viewed":
            profile.meal_views[meal_name] += 1
        
        elif feedback_type == "selected":
            profile.meal_selections[meal_name] += 1
        
        elif feedback_type == "purchased":
            profile.meal_purchases[meal_name] += 1
            if ingredients:
                for ingredient in ingredients:
                    profile.ingredient_purchases[ingredient] += 1
        
        elif feedback_type == "cooked":
            # Track repeat cooking behavior
            if meal_name not in profile.meal_cook_frequency:
                profile.meal_cook_frequency[meal_name] = []
            profile.meal_cook_frequency[meal_name].append(datetime.utcnow())
        
        # Record rating if provided
        if rating:
            if meal_name not in profile.meal_ratings:
                profile.meal_ratings[meal_name] = []
            profile.meal_ratings[meal_name].append(rating)
        
        # Update metadata
        profile.total_interactions += 1
        profile.last_updated = datetime.utcnow()
        
        # Update global popularity
        self.meal_popularity[meal_name] += 1
        
        logger.info(
            f"Recorded {feedback_type} feedback for user {user_id} on meal '{meal_name}'"
        )
    
    def get_recommendations(
        self,
        user_id: str,
        count: int = 5,
        use_history: bool = True
    ) -> List[Dict]:
        """
        Get personalized meal recommendations for a user.
        
        Algorithm:
        1. If user has history: recommend similar meals to favorites
        2. If no history: recommend popular meals
        3. Consider dietary patterns from purchase history
        
        Args:
            user_id: User identifier
            count: Number of recommendations to return
            use_history: Whether to use user's history (True) or return popular meals (False)
            
        Returns:
            List of recommendation dicts with:
            {
                "meal_name": "Egusi Soup",
                "reason": "Similar to your favorite Jollof Rice",
                "confidence": 0.85,
                "popularity_score": 0.92
            }
        """
        recommendations = []
        
        # Get user profile
        profile = self.user_profiles.get(user_id)
        
        if use_history and profile and profile.total_interactions > 0:
            # PERSONALIZED RECOMMENDATIONS (returning user)
            recommendations = self._get_personalized_recommendations(profile, count)
        else:
            # POPULAR RECOMMENDATIONS (new user)
            recommendations = self._get_popular_recommendations(count)
        
        logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
        return recommendations
    
    def _get_personalized_recommendations(
        self,
        profile: UserLearningProfile,
        count: int
    ) -> List[Dict]:
        """Get recommendations based on user history."""
        recommendations = []
        
        # Find user's favorite meals (selected or highly rated)
        favorite_meals = []
        
        # By selection count
        for meal, selections in profile.meal_selections.most_common(3):
            favorite_meals.append((meal, "frequently_selected"))
        
        # By rating
        for meal, ratings in profile.meal_ratings.items():
            avg_rating = sum(ratings) / len(ratings)
            if avg_rating >= 4.0:
                favorite_meals.append((meal, "highly_rated"))
        
        # Find similar meals (same ingredients or cuisine type)
        similar_meals = self._find_similar_meals(favorite_meals)
        
        # Score and rank recommendations
        scored_recommendations = []
        for meal_name, similarity_score in similar_meals.items():
            # Calculate recommendation score
            score = similarity_score
            
            # Boost by global popularity
            popularity = self.meal_popularity.get(meal_name, 0) / max(
                self.meal_popularity.total(), 1
            )
            score += popularity * 0.3
            
            # If user hasn't viewed this meal, it's a good recommendation
            if meal_name not in profile.meal_views:
                score += 0.2
            
            scored_recommendations.append({
                "meal_name": meal_name,
                "score": score,
                "confidence": min(score, 1.0)
            })
        
        # Sort by score and return top N
        scored_recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        for rec in scored_recommendations[:count]:
            recommendations.append({
                "meal_name": rec["meal_name"],
                "reason": "Similar to your favorites",
                "confidence": rec["confidence"],
                "popularity_score": self.meal_popularity.get(rec["meal_name"], 0) / max(
                    self.meal_popularity.total(), 1
                )
            })
        
        return recommendations
    
    def _get_popular_recommendations(self, count: int) -> List[Dict]:
        """Get recommendations based on global popularity."""
        recommendations = []
        
        total_popularity = self.meal_popularity.total()
        if total_popularity == 0:
            # Default meals if no history
            return self._get_default_recommendations(count)
        
        # Normalize popularity scores
        for meal_name, popularity in self.meal_popularity.most_common(count):
            popularity_score = popularity / total_popularity
            
            recommendations.append({
                "meal_name": meal_name,
                "reason": "Popular with other QuickMarket users",
                "confidence": popularity_score,
                "popularity_score": popularity_score
            })
        
        return recommendations
    
    def _find_similar_meals(
        self,
        favorite_meals: List[tuple]
    ) -> Dict[str, float]:
        """
        Find meals similar to user's favorites.
        Uses cuisine type and ingredient overlap.
        """
        # This would connect to a meal similarity database
        # For now, return empty - to be implemented with actual meal data
        similar_meals = {}
        
        # TODO: Implement meal similarity logic
        # - Check cuisine type similarity
        # - Check ingredient overlap
        # - Check cooking time similarity
        
        return similar_meals
    
    def _get_default_recommendations(self, count: int) -> List[Dict]:
        """Get default recommendations for new users with no history."""
        default_meals = [
            {
                "meal_name": "Jollof Rice & Stew",
                "reason": "Popular Nigerian favorite",
                "confidence": 0.9,
                "popularity_score": 0.95
            },
            {
                "meal_name": "Egusi Soup & Swallow",
                "reason": "Traditional and nutritious",
                "confidence": 0.85,
                "popularity_score": 0.88
            },
            {
                "meal_name": "Rice & Beans",
                "reason": "Budget-friendly and protein-rich",
                "confidence": 0.80,
                "popularity_score": 0.92
            },
            {
                "meal_name": "Fried Rice & Egg",
                "reason": "Quick and easy to prepare",
                "confidence": 0.80,
                "popularity_score": 0.85
            },
            {
                "meal_name": "Suya & Pepper",
                "reason": "Delicious and easy",
                "confidence": 0.75,
                "popularity_score": 0.80
            }
        ]
        
        return default_meals[:count]
    
    def get_user_insights(self, user_id: str) -> Dict:
        """
        Get insights about user's meal preferences and patterns.
        
        Returns:
            Dict with:
            {
                "favorite_meals": [...],
                "favorite_ingredients": [...],
                "cooking_frequency": "X meals/month",
                "preferred_meal_types": [...],
                "average_rating": 4.2
            }
        """
        profile = self.user_profiles.get(user_id)
        
        if not profile:
            return {
                "user_id": user_id,
                "status": "new_user",
                "insights": "No meal history yet"
            }
        
        # Calculate insights
        favorite_meals = [
            meal for meal, _ in profile.meal_selections.most_common(3)
        ]
        
        favorite_ingredients = [
            ing for ing, _ in profile.ingredient_purchases.most_common(5)
        ]
        
        # Calculate average rating
        all_ratings = []
        for ratings in profile.meal_ratings.values():
            all_ratings.extend(ratings)
        avg_rating = sum(all_ratings) / len(all_ratings) if all_ratings else 0
        
        # Calculate cooking frequency
        total_cooked = sum(
            len(dates) for dates in profile.meal_cook_frequency.values()
        )
        
        return {
            "user_id": user_id,
            "total_interactions": profile.total_interactions,
            "favorite_meals": favorite_meals,
            "favorite_ingredients": favorite_ingredients,
            "total_meals_cooked": total_cooked,
            "average_rating": round(avg_rating, 2),
            "member_since": profile.created_at.isoformat(),
            "last_active": profile.last_updated.isoformat()
        }
    
    def record_ingredient_removal(
        self,
        user_id: str,
        meal_name: str,
        ingredient_name: str
    ):
        """
        Track when user removes an ingredient from a meal.
        
        Useful for:
        - Understanding dietary restrictions not explicitly stated
        - Improving ingredient mapping
        - Detecting allergens or preferences
        """
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserLearningProfile(user_id)
        
        profile = self.user_profiles[user_id]
        profile.ingredient_removals[ingredient_name] += 1
        profile.last_updated = datetime.utcnow()
        
        logger.info(
            f"User {user_id} removed ingredient '{ingredient_name}' from '{meal_name}'"
        )
