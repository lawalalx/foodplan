from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import UserPreference, User
from schemas.preferences import UserPreferenceData


async def get_latest_user_preferences(
    session: AsyncSession,
    user_id: str
) -> UserPreferenceData:
    """
    Fetch the latest saved preferences for a user.

    Returns:
        UserPreferenceData

    Raises:
        HTTPException(400) if preferences not found
    """

    # Get latest preference record
    result = await session.execute(
        select(UserPreference)
        .where(UserPreference.user_id == user_id)
        .order_by(UserPreference.created_at.desc())
    )
    preference = result.scalars().first()

    if not preference:
        raise HTTPException(
            status_code=400,
            detail="User preferences not set"
        )

    # Fetch household size
    user = await session.get(User, user_id)
    household_size = user.household_size if user else 1

    return UserPreferenceData(
        user_preferences={
            "meals_per_day": (
                preference.meals_per_day.split(",")
                if preference.meals_per_day else []
            ),
            "dietary_restrictions": (
                preference.dietary_restrictions.split(",")
                if preference.dietary_restrictions else []
            ),
            "meal_types": (
                preference.meal_types.split(",")
                if preference.meal_types else []
            ),
        },
        budget_level=preference.budget_level,
        household_size=household_size,
    )
