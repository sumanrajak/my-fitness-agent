from pydantic import BaseModel, Field
from typing import Optional

class UserOnboardForm(BaseModel):
    uid: str
    email: str
    age: int = Field(gt=0)
    sex: str
    height: float = Field(gt=0)
    weight: float = Field(gt=0)
    target_weight: float = Field(gt=0)
    activity_level: str
    context: str
    timeline: str

class UserProfile(UserOnboardForm):
    starting_weight: float
    current_weight: float
    maintenance_calories: Optional[int] = None
    target_calories: Optional[int] = None
    daily_deficit: Optional[int] = None
    insights_summary: Optional[str] = None
    journey_start_date: Optional[str] = None
    last_reanalysis_at: Optional[str] = None
