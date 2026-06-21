import json
# pyrefly: ignore [missing-import]
from google import genai
# pyrefly: ignore [missing-import]
from google.genai import types
from core.config import settings
from utils.fitness_math import compute_calorie_plan
from schemas.ai import CoachInsight, FoodEstimation, ProgressReport, ConsistencyReview, WeeklyAnalysis

client = genai.Client(api_key=settings.GEMINI_API_KEY)

FALLBACK_MODELS = [
 
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-2.0-flash-exp",
    "gemini-pro",
]

def _generate_with_model_fallback(prompt: str, response_schema, temperature: float = 0.2, models: list | None = None) -> dict:
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
    raise last_exc

def analyze_user_fitness(profile_data: dict) -> dict:
    plan = compute_calorie_plan(profile_data)
    
    starting_weight = profile_data.get("starting_weight") or profile_data.get("weight") or 0.0
    weeks_count = max(1, round(plan["days_remaining"] / 7))
    expected_final_weight = round(starting_weight - plan["achievable_kg_by_deadline"], 1)

    if plan["goal_feasible"]:
        feasibility_note = (
            f"This deficit is safe and achievable. The user is on track to lose "
            f"the full {plan['kg_to_lose_requested']} kg by the deadline."
        )
    else:
        feasibility_note = (
            f"IMPORTANT: the exact deficit needed to hit the original "
            f"{plan['kg_to_lose_requested']} kg goal in {plan['days_remaining']} days "
            f"would require eating below a safe minimum. Target calories were "
            f"capped at {plan['target_calories']} kcal/day instead. At this safer "
            f"deficit the user will realistically lose about "
            f"{plan['achievable_kg_by_deadline']} kg by the deadline — NOT the full "
            f"amount requested. You must clearly and explicitly tell the user their "
            f"original deadline is not safely achievable, and suggest a realistic "
            f"extended timeline for the remaining weight loss. Do not gloss over this."
        )

    if not plan["timeline_confidently_parsed"]:
        feasibility_note += (
            " Note: the user's timeline text could not be parsed with confidence; "
            "a default of 12 weeks was used. Ask the user to confirm or clarify their deadline."
        )

    prompt = f"""
    You are an expert fitness coach. Write a short, honest, encouraging insights
    summary for this user based ONLY on the following already-calculated facts.
    Do not recalculate, second-guess, or override any of these numbers — your job
    is only to explain them clearly and motivate the user.

    Facts:
    - Maintenance calories: {plan['maintenance_calories']} kcal/day
    - Target calories: {plan['target_calories']} kcal/day
    - Daily deficit being used: {plan['actual_daily_deficit']} kcal
    - Deficit that would be required to hit the original goal exactly: {plan['required_daily_deficit']} kcal
    - Days remaining until deadline: {plan['days_remaining']}
    - Weight loss requested: {plan['kg_to_lose_requested']} kg
    - Realistically achievable weight loss by deadline: {plan['achievable_kg_by_deadline']} kg
    - Starting weight: {starting_weight} kg
    - Personal context from the user: {profile_data.get('context')}

    {feasibility_note}

    Additionally, generate week-by-week weight predictions starting from Week 0 up to Week {weeks_count}.
    Instructions for `weight_predictions`:
    - Create exactly {weeks_count + 1} points, from Week 0 to Week {weeks_count}.
    - Week 0 weight MUST be exactly {starting_weight} kg.
    - Week {weeks_count} weight MUST be exactly {expected_final_weight} kg.
    - For weeks 1 to {weeks_count - 1}, calculate a realistic weight decay curve between {starting_weight} kg and {expected_final_weight} kg.
    - For each week, provide a short, motivating, and personalized `milestone_note` tailored to the user's goal and context (e.g. if they mentioned gym, specific food preferences, fitness milestones, refer to it organically).
    """

    result = _generate_with_model_fallback(prompt, CoachInsight, temperature=0.3)

    return {
        "maintenance_calories": plan["maintenance_calories"],
        "target_calories": plan["target_calories"],
        "daily_deficit": plan["actual_daily_deficit"],
        "goal_feasible": plan["goal_feasible"],
        "achievable_kg_by_deadline": plan["achievable_kg_by_deadline"],
        "days_remaining": plan["days_remaining"],
        "insights_summary": result.get("insights_summary", ""),
        "weight_predictions": result.get("weight_predictions", []),
    }

def estimate_food_calories(food_text: str) -> dict:
    prompt = f"""
    You are an expert AI nutritionist and calorie estimator.
    Analyze the following meal description: '{food_text}'

    Estimate the total calories as accurately as possible using standard nutritional data.
    Provide a brief, clean itemized breakdown of the components and their individual calories.
    Also estimate the total protein, fiber, and carbohydrates in grams for this meal.
    Return valid JSON with keys: itemized_breakdown, estimated_calories, protein, fiber, carbs.
    """
    return _generate_with_model_fallback(prompt, FoodEstimation, temperature=0.1)

def analyze_progress_report(user_data: dict, daily_log: dict, selected_date: str) -> dict:
    starting_weight = user_data.get("starting_weight", user_data.get("weight", "N/A"))
    current_weight = daily_log.get("weight") or user_data.get("current_weight", user_data.get("weight", "N/A"))
    target_calories = user_data.get("target_calories", 0)
    daily_calories = daily_log.get("total_consumed", 0)
    daily_protein = daily_log.get("total_protein", 0)
    daily_fiber = daily_log.get("total_fiber", 0)
    daily_carbs = daily_log.get("total_carbs", 0)
    steps = daily_log.get("steps", 0)
    exercise_minutes = daily_log.get("exercise_minutes", 0)
    activity_description = daily_log.get("activity_description", "No activity details provided.")
    timeline = user_data.get("timeline", "unspecified timeline")

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
    1. "status_summary"
    2. "change_observation"
    3. "coach_recommendation"
    """

    return _generate_with_model_fallback(prompt, ProgressReport, temperature=0.3)

def analyze_consistency_review(user_data: dict, recent_summaries: list = None) -> dict:
    target_calories = user_data.get("target_calories", 0)
    recent_data = ""
    if recent_summaries:
        recent_data = "\n".join([
            f"- {day['date']}: {day['total_consumed']} kcal, {day.get('logs_count', 0)} items"
            for day in recent_summaries
        ])

    prompt = f"""
    You are an expert fitness coach asked to evaluate a client's recent calorie tracking consistency.

    User Profile:
    - Target Calories: {target_calories} kcal
    - Target Timeline: {user_data.get('timeline', 'N/A')}
    - Personal Context: {user_data.get('context', 'N/A')}

    Recent Tracking:
    {recent_data or 'No recent daily intake summary available.'}

    Return valid JSON with exactly two keys:
    1. "status_evaluation"
    2. "actionable_tip"
    """
    return _generate_with_model_fallback(prompt, ConsistencyReview, temperature=0.25)

def analyze_weekly_report(daily_summaries: list, target_daily: int, total_consumed: int, estimated_weight_loss: float, user_data: dict = None) -> dict:
    total_target = target_daily * len(daily_summaries) if daily_summaries else target_daily * 7
    net_deficit = total_target - total_consumed

    daily_breakdown = "\n".join([f"  {d['date']}: {d['total_consumed']} kcal" for d in daily_summaries])

    user_context = f"""
    User Profile:
    - Current Weight: {user_data.get('current_weight', 'N/A')} kg
    - Target Weight: {user_data.get('target_weight', 'N/A')} kg
    - Maintenance Calories: {user_data.get('maintenance_calories', 'N/A')} kcal
    - Target Calories: {user_data.get('target_calories', 'N/A')} kcal
    """ if user_data else ""

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
    1. "status_summary"
    2. "coach_verdict"
    3. "detailed_insights"
    """
    return _generate_with_model_fallback(prompt, WeeklyAnalysis, temperature=0.3)
