from pydantic import BaseModel
from typing import List, Optional

class MealLog(BaseModel):
    timestamp: str
    meal_type: str
    input_text: str
    breakdown: str
    calories: int
    protein: float
    fiber: float
    carbs: float

class DailyTracking(BaseModel):
    date: str
    weight: float
    activity_description: str = ""
    steps: int = 0
    exercise_minutes: int = 0
    total_consumed: int = 0
    total_protein: float = 0
    total_fiber: float = 0
    total_carbs: float = 0
    logs: List[MealLog] = []

class DailyCheckInForm(BaseModel):
    uid: str
    date: str
    weight: float
    activity_description: str = ""
    steps: int = 0
    exercise_minutes: int = 0

class LogCaloriesForm(BaseModel):
    uid: str
    date: str
    meal_type: str
    food_description: str
