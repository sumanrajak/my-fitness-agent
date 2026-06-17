from pydantic import BaseModel
from google import genai
from google.genai import types
from config import settings
import json

# Initialize the new GenAI Client
# It automatically looks for the GEMINI_API_KEY environment variable
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Define the expected structured output schema using Pydantic
class CalorieAnalysis(BaseModel):
    maintenance_calories: int
    target_calories: int
    insights_summary: str

def analyze_user_fitness(profile_data: dict) -> dict:
    """
    Sends user details to Gemini using the new google-genai SDK 
    and returns a validated dictionary matching the CalorieAnalysis schema.
    """
    
    prompt = f"""
    You are an expert fitness coach and AI agent. Analyze the following user profile:
    - Age: {profile_data.get('age')}
    - Biological Sex: {profile_data.get('sex')}
    - Height: {profile_data.get('height')} cm
    - Current Weight: {profile_data.get('weight')} kg
    - Activity Level: {profile_data.get('activity_level')}
    - Personal Context & Insights: {profile_data.get('context')}
    - Target Timeline: {profile_data.get('timeline')}
    
    Calculate their exact daily maintenance calories and target calories to safely reach their goal within their timeline. 
    Provide a concise summary of insights.
    """
    
    # Using the recommended 'gemini-2.5-flash' model for text tasks
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CalorieAnalysis,
            temperature=0.2, # Lower temperature for more stable calculations
        ),
    )
    
    # The SDK parses it directly into the schema if requested, 
    # but since it returns valid JSON matching our Pydantic object, we can safely parse it
    return json.loads(response.text)

class FoodEstimation(BaseModel):
    itemized_breakdown: str  # e.g., "Eggs (140 kcal), Toast (150 kcal)"
    estimated_calories: int  # e.g., 290

def estimate_food_calories(food_text: str) -> dict:
    """
    Uses Gemini 1.5 Flash to analyze a natural language food description
    and return an estimated calorie count with an itemized breakdown.
    """
    prompt = f"""
    You are an expert AI nutritionist and calorie estimator. 
    Analyze the following meal description: '{food_text}'
    
    Estimate the total calories as accurately as possible based on standard nutritional data.
    Provide a brief, clean itemized breakdown text of the components and their individual calories.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FoodEstimation,
            temperature=0.1,  # Low temperature for objective calorie calculations
        ),
    )
    
    return json.loads(response.text)

class WeeklyAnalysis(BaseModel):
    status_summary: str
    coach_verdict: str
    detailed_insights: str

def analyze_weekly_report(daily_summaries: list, target_daily: int, total_consumed: int, estimated_weight_loss: float, user_data: dict = None) -> dict:
    """
    Analyzes a full week of calorie tracking and provides comprehensive report.
    
    Args:
        daily_summaries: List of daily logs with date and total_consumed
        target_daily: Target calories per day
        total_consumed: Total calories consumed in the week
        estimated_weight_loss: Calculated weight loss/gain based on calorie deficit
        user_data: Optional user profile data (weight, height, age, sex, etc.)
    
    Returns:
        Dictionary with status_summary, coach_verdict, and detailed_insights
    """
    total_target = target_daily * 7
    net_deficit = total_target - total_consumed
    
    daily_breakdown = "\n".join([f"  {d['date']}: {d['total_consumed']} kcal" for d in daily_summaries])
    
    # Build user context if data is provided
    user_context = ""
    if user_data:
        user_context = f"""
    User Profile:
    - Age: {user_data.get('age', 'N/A')}
    - Sex: {user_data.get('sex', 'N/A')}
    - Height: {user_data.get('height', 'N/A')} cm
    - Current Weight: {user_data.get('weight', 'N/A')} kg
    - Activity Level: {user_data.get('activity_level', 'N/A')}
    - Maintenance Calories: {user_data.get('maintenance_calories', 'N/A')} kcal
    - Personal Context: {user_data.get('context', 'N/A')}
    - Target Timeline: {user_data.get('timeline', 'N/A')}
    """
    
    prompt = f"""
    You are an expert fitness coach analyzing a client's weekly calorie tracking performance.
    {user_context}
    
    Weekly Summary:
    - Daily Target: {target_daily} kcal
    - Total Weekly Target: {total_target} kcal
    - Total Consumed: {total_consumed} kcal
    - Net Deficit: {net_deficit} kcal
    - Estimated Weight Loss/Gain: {round(estimated_weight_loss, 2)} kg
    
    Daily Breakdown:
    {daily_breakdown}
    
    Provide a detailed weekly analysis in JSON format with:
    1. "status_summary": A concise 2-3 sentence assessment of their progress (consider their personal goals and timeline)
    2. "coach_verdict": Your professional recommendation for next week based on their profile and performance
    3. "detailed_insights": Specific observations about their tracking patterns, meal distribution, and personalized suggestions
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=WeeklyAnalysis,
            temperature=0.3,  # Slightly higher for more personalized insights
        ),
    )
    
    return json.loads(response.text)