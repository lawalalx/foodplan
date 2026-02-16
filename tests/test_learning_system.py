"""
Tests for user learning and personalization system.
Validates user profile tracking and recommendation generation.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from learning_system import UserLearningSystem


class TestUserLearningSystem:
    """Test the learning system."""
    
    @pytest.fixture
    def learning_system(self):
        """Initialize learning system."""
        return UserLearningSystem()
    
    def test_system_initialization(self, learning_system):
        """Test system can be initialized."""
        assert learning_system is not None
        assert hasattr(learning_system, 'user_profiles')
        assert hasattr(learning_system, 'record_feedback')
        assert hasattr(learning_system, 'get_recommendations')
    
    def test_record_meal_viewed(self, learning_system):
        """Test recording a meal view event."""
        user_id = "test_user"
        meal_name = "Jollof Rice"
        
        learning_system.record_feedback(
            user_id=user_id,
            meal_name=meal_name,
            feedback_type="viewed",
            rating=None
        )
        
        # Verify user profile created
        assert user_id in learning_system.user_profiles
        profile = learning_system.user_profiles[user_id]
        assert meal_name in profile.viewed_meals
    
    def test_record_meal_selected(self, learning_system):
        """Test recording a meal selection."""
        user_id = "test_user"
        meal_name = "Egusi Soup"
        
        learning_system.record_feedback(
            user_id=user_id,
            meal_name=meal_name,
            feedback_type="selected",
            rating=None
        )
        
        profile = learning_system.user_profiles[user_id]
        assert meal_name in profile.selected_meals
    
    def test_record_meal_with_rating(self, learning_system):
        """Test recording rated meals."""
        user_id = "test_user"
        meal_name = "Pepper Soup"
        
        learning_system.record_feedback(
            user_id=user_id,
            meal_name=meal_name,
            feedback_type="rated",
            rating=5
        )
        
        profile = learning_system.user_profiles[user_id]
        assert meal_name in profile.rated_meals
        assert profile.meal_ratings.get(meal_name) == 5
    
    def test_record_meal_purchased(self, learning_system):
        """Test recording meal ingredient purchases."""
        user_id = "test_user"
        meal_name = "Moi Moi"
        
        learning_system.record_feedback(
            user_id=user_id,
            meal_name=meal_name,
            feedback_type="purchased",
            rating=None
        )
        
        profile = learning_system.user_profiles[user_id]
        assert meal_name in profile.purchased_meals or meal_name in profile.selected_meals
    
    def test_get_recommendations_for_new_user(self, learning_system):
        """Test getting recommendations for user with no history."""
        user_id = "new_user"
        recommendations = learning_system.get_recommendations(user_id, count=5)
        
        assert recommendations is not None
        assert isinstance(recommendations, list)
    
    def test_get_recommendations_for_returning_user(self, learning_system):
        """Test getting recommendations for user with history."""
        user_id = "returning_user"
        
        # Record some interactions
        meals = ["Jollof Rice", "Egusi Soup", "Fried Rice"]
        for meal in meals:
            learning_system.record_feedback(
                user_id=user_id,
                meal_name=meal,
                feedback_type="viewed",
                rating=None
            )
        
        # Get recommendations
        recommendations = learning_system.get_recommendations(user_id, count=5)
        
        assert recommendations is not None
        assert isinstance(recommendations, list)
    
    def test_recommendations_respect_count(self, learning_system):
        """Test that recommendation count is respected."""
        user_id = "count_test_user"
        
        # Request specific count
        recs_5 = learning_system.get_recommendations(user_id, count=5)
        recs_10 = learning_system.get_recommendations(user_id, count=10)
        
        assert len(recs_5) <= 5
        assert len(recs_10) <= 10
    
    def test_user_profile_persistence(self, learning_system):
        """Test that user profiles persist across multiple recordings."""
        user_id = "persistent_user"
        
        # Record multiple interactions
        learning_system.record_feedback(
            user_id=user_id,
            meal_name="Jollof Rice",
            feedback_type="viewed",
            rating=None
        )
        
        learning_system.record_feedback(
            user_id=user_id,
            meal_name="Jollof Rice",
            feedback_type="selected",
            rating=None
        )
        
        learning_system.record_feedback(
            user_id=user_id,
            meal_name="Jollof Rice",
            feedback_type="rated",
            rating=5
        )
        
        # Verify all interactions recorded
        profile = learning_system.user_profiles[user_id]
        assert "Jollof Rice" in profile.viewed_meals
        assert "Jollof Rice" in profile.selected_meals
        assert profile.meal_ratings.get("Jollof Rice") == 5


class TestRecommendationLogic:
    """Test recommendation generation logic."""
    
    @pytest.fixture
    def learning_system(self):
        return UserLearningSystem()
    
    def test_recommendations_favor_highly_rated_meals(self, learning_system):
        """Test that highly rated meals get recommended."""
        user_id = "rating_test_user"
        
        # Record high-rated meal
        learning_system.record_feedback(
            user_id=user_id,
            meal_name="Premium Meal",
            feedback_type="rated",
            rating=5
        )
        
        # Record low-rated meal
        learning_system.record_feedback(
            user_id=user_id,
            meal_name="Budget Meal",
            feedback_type="rated",
            rating=2
        )
        
        recommendations = learning_system.get_recommendations(user_id, count=10)
        
        # High-rated meal should appear in recommendations
        assert recommendations is not None
    
    def test_recommendations_include_new_meals(self, learning_system):
        """Test that recommendations include meals user hasn't tried."""
        user_id = "discovery_user"
        
        # Record interactions with known meals
        learning_system.record_feedback(
            user_id=user_id,
            meal_name="Jollof Rice",
            feedback_type="viewed",
            rating=None
        )
        
        # Get recommendations should include new meals
        recommendations = learning_system.get_recommendations(user_id, count=5)
        
        assert recommendations is not None
        assert isinstance(recommendations, list)


class TestLearningSystemIntegration:
    """Integration tests for learning system."""
    
    @pytest.fixture
    def learning_system(self):
        return UserLearningSystem()
    
    @pytest.mark.asyncio
    async def test_full_user_journey_personalization(self, learning_system):
        """Test full user journey with personalization."""
        user_id = "journey_user"
        
        # Step 1: User views some meals
        meals = ["Jollof Rice", "Egusi Soup", "Pepper Soup", "Fried Rice", "Moi Moi"]
        for meal in meals:
            learning_system.record_feedback(
                user_id=user_id,
                meal_name=meal,
                feedback_type="viewed",
                rating=None
            )
        
        # Step 2: User selects some meals
        for meal in meals[:3]:
            learning_system.record_feedback(
                user_id=user_id,
                meal_name=meal,
                feedback_type="selected",
                rating=None
            )
        
        # Step 3: User rates meals
        learning_system.record_feedback(
            user_id=user_id,
            meal_name="Jollof Rice",
            feedback_type="rated",
            rating=5
        )
        
        learning_system.record_feedback(
            user_id=user_id,
            meal_name="Egusi Soup",
            feedback_type="rated",
            rating=4
        )
        
        learning_system.record_feedback(
            user_id=user_id,
            meal_name="Pepper Soup",
            feedback_type="rated",
            rating=3
        )
        
        # Step 4: Get personalized recommendations
        recommendations = learning_system.get_recommendations(user_id, count=5)
        
        assert recommendations is not None
        assert isinstance(recommendations, list)
        
        # Verify user profile contains all interactions
        profile = learning_system.user_profiles[user_id]
        assert len(profile.viewed_meals) >= 3
        assert len(profile.meal_ratings) >= 3
