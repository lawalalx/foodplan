"""
Database models for meal planning system using SQLModel.
Supports both new users (preference-based) and returning users (history-based).
Production-ready with zero demo data.
"""
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON, Column
from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid


class User(SQLModel, table=True):
    """User entity - from existing backend."""
    __tablename__ = "meal_planning_users"
    
    user_id: str = Field(primary_key=True, index=True)
    phone_number: Optional[str] = None
    household_size: int = 1
    is_new_user: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    preferences: List["UserPreference"] = Relationship(back_populates="user")
    meal_plans: List["MealPlan"] = Relationship(back_populates="user")
    purchase_history: List["PurchaseHistory"] = Relationship(back_populates="user")
    meal_feedback: List["MealFeedback"] = Relationship(back_populates="user")


class UserPreference(SQLModel, table=True):
    """User preferences for meal planning."""
    __tablename__ = "meal_planning_user_preferences"
    
    preference_id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="meal_planning_users.user_id")
    
    # Dietary preferences
    meal_duration: str = "weekly"  # "weekly", "monthly"
    meals_per_day: str = "breakfast,lunch,dinner"  # comma-separated
    dietary_restrictions: Optional[str] = None  # comma-separated
    meal_types: Optional[str] = None  # comma-separated
    budget_level: Optional[str] = None  # "budget-friendly", "moderate", "premium"
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="preferences")


class MealPlan(SQLModel, table=True):
    """Generated meal plan for a user."""
    __tablename__ = "meal_planning_plans"
    
    meal_plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="meal_planning_users.user_id", index=True)
    
    # Plan metadata
    duration: str  # "weekly", "monthly"
    start_date: datetime
    end_date: datetime
    
    # Plan content (stored as JSON for flexibility)
    plan_content: dict = Field(sa_column=Column(JSON, nullable=False), default_factory=dict)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    used: bool = False
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="meal_plans")
    meals: List["PlanMeal"] = Relationship(back_populates="meal_plan")


class PlanMeal(SQLModel, table=True):
    """Meals within a meal plan."""
    __tablename__ = "meal_planning_plan_meals"
    
    plan_meal_id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    meal_plan_id: str = Field(foreign_key="meal_planning_plans.meal_plan_id", index=True)
    
    # Meal details
    meal_name: str
    meal_type: str  # "breakfast", "lunch", "dinner"
    day_order: int  # 1 for Monday, 2 for Tuesday, etc.
    
    # AI-generated details
    description: Optional[str] = None
    estimated_cook_time: Optional[int] = None  # minutes
    
    viewed: bool = False
    selected: bool = False
    added_to_cart: bool = False
    
    # Relationships
    meal_plan: Optional[MealPlan] = Relationship(back_populates="meals")
    ingredients: List["PlanMealIngredient"] = Relationship(back_populates="plan_meal")


class PlanMealIngredient(SQLModel, table=True):
    """Ingredients for a meal in a plan."""
    __tablename__ = "meal_planning_ingredients"
    
    ingredient_id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    plan_meal_id: str = Field(foreign_key="meal_planning_plan_meals.plan_meal_id", index=True)
    
    # Ingredient details
    ingredient_name: str
    quantity: float
    unit: str  # "kg", "ml", "pieces", "cups"
    
    # QuickMarket mapping
    mapped_product_id: Optional[str] = None
    product_name: Optional[str] = None
    product_price: Optional[float] = None
    availability_status: str = "unknown"  # "available", "unavailable", "substitute"
    substitute_product_id: Optional[str] = None
    
    # User interaction
    removed_by_user: bool = False
    quantity_adjusted: Optional[float] = None
    
    # Relationships
    plan_meal: Optional[PlanMeal] = Relationship(back_populates="ingredients")


class PurchaseHistory(SQLModel, table=True):
    """User purchase history - used for personalization."""
    __tablename__ = "meal_planning_purchase_history"
    
    purchase_id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="meal_planning_users.user_id", index=True)
    
    # Purchase details
    product_id: str
    product_name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    price: Optional[float] = None
    
    # Categorization
    ingredient_category: Optional[str] = None
    purchase_date: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="purchase_history")


class MealFeedback(SQLModel, table=True):
    """User feedback on meals - for learning and personalization."""
    __tablename__ = "meal_planning_feedback"
    
    feedback_id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="meal_planning_users.user_id", index=True)
    plan_meal_id: Optional[str] = None
    
    # Feedback types
    meal_viewed: bool = False
    meal_selected: bool = False
    ingredients_added_to_cart: bool = False
    ingredients_removed: int = 0
    meal_cooked: bool = False
    user_rating: Optional[int] = None  # 1-5 rating
    
    # Feedback timestamp
    feedback_date: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="meal_feedback")


class Ingredient(SQLModel, table=True):
    """Global ingredient catalog - used for mapping."""
    __tablename__ = "meal_planning_ingredient_catalog"
    
    ingredient_id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Ingredient details
    name: str = Field(unique=True, index=True)
    category: Optional[str] = None
    nigerian_names: Optional[str] = None  # comma-separated aliases
    
    # Nutrition info (per 100g)
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    carbs_g: Optional[float] = None
    
    # Product mapping
    default_unit: str = "kg"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MealTemplate(SQLModel, table=True):
    """Template meals for quick reference in meal plan generation."""
    __tablename__ = "meal_planning_templates"
    
    template_id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Meal details
    meal_name: str = Field(unique=True, index=True)
    description: Optional[str] = None
    cuisine_type: Optional[str] = None
    difficulty_level: Optional[str] = None
    estimated_cook_time: Optional[int] = None
    
    # Nutrition (per serving)
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    
    # Default ingredients (baseline)
    base_ingredients: dict = Field(sa_column=Column(JSON, nullable=False), default_factory=dict)
    
    # Dietary attributes
    is_vegetarian: bool = False
    is_vegan: bool = False
    is_gluten_free: bool = False
    
    popularity_score: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
