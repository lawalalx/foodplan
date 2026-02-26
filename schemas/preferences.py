from pydantic import BaseModel
from typing import Dict, List


class UserPreferenceData(BaseModel):
    user_preferences: Dict[str, List[str]]
    budget_level: str
    household_size: int
