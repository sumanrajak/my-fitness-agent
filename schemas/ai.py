from pydantic import BaseModel
from typing import Dict, List

class WeightPredictionPoint(BaseModel):
    week: int
    date: str
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
    diet_analysis: str

class ConsistencyReview(BaseModel):
    status_evaluation: str
    actionable_tip: str

class CravingSupport(BaseModel):
    headline: str
    message: str
    immediate_actions: List[str]
    motivation: str
    safety_note: str
    friend_note: str
    challenge: str
    money_ideas: List[str]

class RecipeIngredient(BaseModel):
    name: str
    raw_weight_g: float
    preparation: str

class RecipeMacros(BaseModel):
    calories: int
    protein_g: float
    fiber_g: float
    carbs_g: float
    fat_g: float

class MealRecommendation(BaseModel):
    recipe_name: str
    why_this_meal: str
    ingredients: List[RecipeIngredient]
    steps: List[str]
    macros: RecipeMacros
    fit_summary: str
    safety_note: str

class WeeklyAnalysis(BaseModel):
    status_summary: str
    coach_verdict: str
    detailed_insights: str
