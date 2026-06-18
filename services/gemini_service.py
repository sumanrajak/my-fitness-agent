from pydantic import BaseModel
from google import genai
from google.genai import types
from config import settings
import json
from datetime import datetime

# Initialize the new GenAI Client
# It automatically looks for the GEMINI_API_KEY environment variable
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Define the expected structured output schema using Pydantic
class CalorieAnalysis(BaseModel):
    maintenance_calories: int
    target_calories: int
    insights_summary: str

# Primary + fallback Gemini models
FALLBACK_MODELS = [
    "gemini-3-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
]


def _generate_with_model_fallback(prompt: str, response_schema, temperature: float = 0.2, models: list | None = None) -> dict:
    """Try the supplied Gemini models in order until one succeeds.

    Returns the parsed JSON dict from the first successful response. Raises the last
    exception if all models fail.
    """
    models = models or FALLBACK_MODELS
    last_exc = None
    for model in models:
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=temperature,
                ),
            )
            return json.loads(resp.text)
        except Exception as e:
            print(f"Gemini model {model} failed: {e}")
            last_exc = e
            continue
    # If we reach here, all models failed
    raise last_exc

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
    - Target Weight: {profile_data.get('target_weight', 'N/A')} kg
    - Activity Level: {profile_data.get('activity_level')}
    - Personal Context & Insights: {profile_data.get('context')}
    - Target Timeline: {profile_data.get('timeline')} (e.g., July 30th)
    - Today's date: {datetime.today().strftime('%Y-%m-%d')}

    CRITICAL MATH REQUIREMENT:
    1. Calculate the exact total weight loss required to reach the target weight.
    2. Determine the precise number of weeks available until the deadline.
    3. Calculate the exact mathematical daily caloric deficit required to achieve this specific weight loss by the deadline (using the rule: 1kg of fat ≈ 7,700 kcal, or 1lb ≈ 3,500 kcal). Do NOT default to a standard 500-kcal deficit if it does not match the timeline math.
    4. Subtract this exact deficit from the daily maintenance calories to find the absolute target calories.
    5. Ensure the week-by-week weight estimation perfectly aligns with this calculated caloric deficit.

    Provide a summary of insights including maintenance calories, the exact calculated daily caloric deficit, the resulting target calories, and a mathematically consistent weekwise weight estimation.

    Return valid JSON with keys: maintenance_calories, target_calories, insights_summary.
    """
    
    # Try multiple Gemini models (fallbacks) until one succeeds
    return _generate_with_model_fallback(prompt, CalorieAnalysis, temperature=0.2)

class FoodEstimation(BaseModel):
    itemized_breakdown: str  # e.g., "Eggs (140 kcal), Toast (150 kcal)"
    estimated_calories: int  # e.g., 290
    protein: int
    fiber: int
    carbs: int

def estimate_food_calories(food_text: str) -> dict:
    """
    Uses Gemini 1.5 Flash to analyze a natural language food description
    and return an estimated calorie count with an itemized breakdown and macros.
    """
    prompt = f"""
    You are an expert AI nutritionist and calorie estimator.
    Analyze the following meal description: '{food_text}'
    
    Estimate the total calories as accurately as possible using standard nutritional data.
    Provide a brief, clean itemized breakdown of the components and their individual calories.
    Also estimate the total protein, fiber, and carbohydrates in grams for this meal.
    Return valid JSON with keys: itemized_breakdown, estimated_calories, protein, fiber, carbs.
    """
    
    try:
        return _generate_with_model_fallback(prompt, FoodEstimation, temperature=0.1)
    except Exception:
        # If Gemini model family fails entirely, surface the error to caller
        raise

class WeeklyAnalysis(BaseModel):
    status_summary: str
    coach_verdict: str
    detailed_insights: str

class ProgressReport(BaseModel):
    status_summary: str
    change_observation: str
    coach_recommendation: str

class ConsistencyReview(BaseModel):
    status_evaluation: str
    actionable_tip: str

def analyze_progress_report(user_data: dict, daily_log: dict, selected_date: str) -> dict:
    """
    Generates a day-wise progress report using the user's goal, starting weight, current day weight, and calorie/activity log.
    """
    starting_weight = user_data.get('starting_weight', user_data.get('weight', 'N/A'))
    current_weight = daily_log.get('weight', user_data.get('weight', user_data.get('weight', 'N/A')))
    target_calories = user_data.get('target_calories', 0)
    daily_calories = daily_log.get('total_consumed', 0)
    daily_protein = daily_log.get('total_protein', 0)
    daily_fiber = daily_log.get('total_fiber', 0)
    daily_carbs = daily_log.get('total_carbs', 0)
    steps = daily_log.get('steps', 0)
    exercise_minutes = daily_log.get('exercise_minutes', 0)
    activity_description = daily_log.get('activity_description', 'No activity details provided.')
    timeline = user_data.get('timeline', 'unspecified timeline')

    prompt = f"""
    You are an expert fitness coach. Create a day-wise progress report for a client using these details.

    User Profile:
    - Age: {user_data.get('age', 'N/A')}
    - Sex: {user_data.get('sex', 'N/A')}
    - Height: {user_data.get('height', 'N/A')} cm
    - Starting Weight: {starting_weight} kg
    - Current Weight: {current_weight} kg
    - Target Weight: {user_data.get('target_weight', 'N/A')} kg
    - Activity Level: {user_data.get('activity_level', 'N/A')}
    - Target Calories: {target_calories} kcal
    - Timeline Goal: {timeline}
    - Context: {user_data.get('context', 'N/A')}

    Today's Tracking ({selected_date}):
    - Calories Logged: {daily_calories} kcal
    - Protein: {daily_protein} g
    - Fiber: {daily_fiber} g
    - Carbs: {daily_carbs} g
    - Steps: {steps}
    - Exercise Minutes: {exercise_minutes}
    - Activity Notes: {activity_description}

    Return valid JSON with exactly three keys:
    1. "status_summary" -  about today's progress toward the goal and motivate if needed.
    2. "change_observation" - one specific observation comparing today's weight or calories to the starting goal.
    3. "coach_recommendation" - one practical recommendation for the next day add exactly how much weeks will it take to reach my goal.
    """

    return _generate_with_model_fallback(prompt, ProgressReport, temperature=0.3)


def analyze_consistency_review(user_data: dict, recent_summaries: list = None) -> dict:
    """
    Generates a quick coach-style consistency review for the user based on recent tracking.
    """
    target_calories = user_data.get('target_calories', 0)
    recent_data = ""
    if recent_summaries:
        recent_data = "\n".join([
            f"- {day['date']}: {day['total_consumed']} kcal, {day.get('logs_count', 0)} items"
            for day in recent_summaries
        ])

    prompt = f"""
    You are an expert fitness coach asked to evaluate a client's recent calorie tracking consistency.
    Use the user's profile and intake data to provide a short assessment and one practical tip.

    User Profile:
    - Age: {user_data.get('age', 'N/A')}
    - Sex: {user_data.get('sex', 'N/A')}
    - Height: {user_data.get('height', 'N/A')} cm
    - Current Weight: {user_data.get('weight', 'N/A')} kg
    - Target Weight: {user_data.get('target_weight', 'N/A')} kg
    - Activity Level: {user_data.get('activity_level', 'N/A')}
    - Target Calories: {target_calories} kcal
    - Target Timeline: {user_data.get('timeline', 'N/A')}
    - Personal Context: {user_data.get('context', 'N/A')}

    Recent Tracking:
    {recent_data or 'No recent daily intake summary available.'}

    Based on this information, return valid JSON with exactly two keys:
    1. "status_evaluation" - a short statement about whether they are consistent with their goals.
    2. "actionable_tip" - one practical recommendation for the next day or week.
    """

    return _generate_with_model_fallback(prompt, ConsistencyReview, temperature=0.25)


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
    - Target Weight: {user_data.get('target_weight', 'N/A')} kg
    - Activity Level: {user_data.get('activity_level', 'N/A')}
    - Maintenance Calories: {user_data.get('maintenance_calories', 'N/A')} kcal
    - Target Calories: {user_data.get('target_calories', 'N/A')} kcal
    - Target Timeline: {user_data.get('timeline', 'N/A')}
    - Personal Context: {user_data.get('context', 'N/A')}
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
    
    return _generate_with_model_fallback(prompt, WeeklyAnalysis, temperature=0.3)