from pydantic import BaseModel
from typing import List

class WeightPredictionPoint(BaseModel):
    week: int
    weight: float
    milestone_note: str

class CoachInsight(BaseModel):
    insights_summary: str
    weight_predictions: List[WeightPredictionPoint]

class FoodEstimation(BaseModel):
    itemized_breakdown: str
    estimated_calories: int
    protein: int
    fiber: int
    carbs: int

class ProgressReport(BaseModel):
    status_summary: str
    change_observation: str
    coach_recommendation: str

class ConsistencyReview(BaseModel):
    status_evaluation: str
    actionable_tip: str

class WeeklyAnalysis(BaseModel):
    status_summary: str
    coach_verdict: str
    detailed_insights: str
