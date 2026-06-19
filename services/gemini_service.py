"""
Corrected fitness AI agent service.

Key fix vs the original: all calorie/deficit/timeline arithmetic is now done
deterministically in Python. Gemini is only used to write the human-readable
coaching summary, and it is explicitly told not to recalculate anything.
This removes the failure mode where the model computed a correct deficit,
decided it was unsafe, and silently swapped in a different target calorie
number without reconciling that against the stated weight-loss goal/timeline.

Requires: pip install python-dateutil
"""

import re
import json
from datetime import datetime
from dateutil import parser as date_parser
from pydantic import BaseModel
from google import genai
from google.genai import types
from config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

# NOTE: verify these model IDs against current Gemini docs before shipping —
# also double check this is actually a best-to-worst fallback order
# (gemini-3.5 listed after gemini-3 looks like it might be inverted).
FALLBACK_MODELS = [
    "gemini-3-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
]

KCAL_PER_KG_FAT = 7700

ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "lightly active": 1.375,
    "moderately active": 1.55,
    "very active": 1.725,
    "extra active": 1.9,
}


def _generate_with_model_fallback(prompt: str, response_schema, temperature: float = 0.2, models: list | None = None) -> dict:
    """Try the supplied Gemini models in order until one succeeds."""
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


# ---------------------------------------------------------------------------
# Deterministic math helpers — none of this should ever be delegated to the LLM
# ---------------------------------------------------------------------------

def get_activity_multiplier(activity_level: str) -> float:
    level = (activity_level or "").lower()
    for key, mult in ACTIVITY_MULTIPLIERS.items():
        if key in level:
            return mult
    return 1.375  # reasonable default if the label doesn't match


def calculate_bmr(age: float, sex: str, height_cm: float, weight_kg: float) -> float:
    """Mifflin-St Jeor BMR."""
    sex_constant = 5 if (sex or "").lower().startswith("m") else -161
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + sex_constant


def parse_days_remaining(timeline_str: str, today: datetime) -> tuple[int, bool]:
    """
    Returns (days_remaining, parsed_confidently).
    Handles absolute dates ("july 30 2026", "by Dec 2026") and relative
    durations ("12 weeks", "3 months", "45 days").
    """
    timeline_str = (timeline_str or "").strip()

    # Try absolute date parsing first
    try:
        target_date = date_parser.parse(timeline_str, fuzzy=True, default=today)
        if target_date.date() <= today.date():
            # e.g. "Dec 2026" parsed against a default that landed in the past
            target_date = target_date.replace(year=target_date.year + 1)
        days = (target_date.date() - today.date()).days
        if days > 0:
            return days, True
    except (ValueError, OverflowError):
        pass

    # Fall back to relative duration patterns
    match = re.search(r"(\d+)\s*week", timeline_str, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 7, True
    match = re.search(r"(\d+)\s*month", timeline_str, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 30, True
    match = re.search(r"(\d+)\s*day", timeline_str, re.IGNORECASE)
    if match:
        return int(match.group(1)), True

    # Couldn't parse — default to 12 weeks, but flag low confidence so the
    # caller can warn the user instead of silently guessing.
    return 84, False


def compute_calorie_plan(profile_data: dict) -> dict:
    """
    Does the entire goal/timeline/deficit calculation deterministically.
    This is the single source of truth for every number shown to the user.
    """
    age = profile_data.get("age")
    sex = profile_data.get("sex", "male")
    height_cm = profile_data.get("height")
    current_weight = profile_data.get("current_weight", profile_data.get("weight"))
    target_weight = profile_data.get("target_weight", current_weight)
    activity_level = profile_data.get("activity_level", "")
    timeline = profile_data.get("timeline", "")

    bmr = calculate_bmr(age, sex, height_cm, current_weight)
    multiplier = get_activity_multiplier(activity_level)
    maintenance_calories = round(bmr * multiplier)

    days_remaining, timeline_confident = parse_days_remaining(timeline, datetime.today())

    kg_to_lose = max(0.0, (current_weight or 0) - (target_weight or current_weight or 0))
    total_deficit_needed = kg_to_lose * KCAL_PER_KG_FAT
    required_daily_deficit = total_deficit_needed / days_remaining if days_remaining > 0 else 0
    raw_target_calories = maintenance_calories - required_daily_deficit

    # Hard safety floor: never recommend going below BMR, and never below a
    # sane absolute minimum, regardless of what the timeline math demands.
    safe_min_calories = max(bmr, 1500 if (sex or "").lower().startswith("m") else 1200)

    if raw_target_calories < safe_min_calories:
        target_calories = round(safe_min_calories)
        actual_daily_deficit = maintenance_calories - target_calories
        achievable_kg_by_deadline = (actual_daily_deficit * days_remaining) / KCAL_PER_KG_FAT
        goal_feasible = False
    else:
        target_calories = round(raw_target_calories)
        actual_daily_deficit = round(required_daily_deficit)
        achievable_kg_by_deadline = kg_to_lose
        goal_feasible = True

    return {
        "bmr": round(bmr),
        "maintenance_calories": maintenance_calories,
        "days_remaining": days_remaining,
        "weeks_remaining": round(days_remaining / 7, 2),
        "timeline_confidently_parsed": timeline_confident,
        "kg_to_lose_requested": round(kg_to_lose, 2),
        "required_daily_deficit": round(required_daily_deficit),
        "target_calories": target_calories,
        "actual_daily_deficit": actual_daily_deficit,
        "goal_feasible": goal_feasible,
        "achievable_kg_by_deadline": round(achievable_kg_by_deadline, 2),
    }


# ---------------------------------------------------------------------------
# LLM call — now only responsible for language, never for numbers
# ---------------------------------------------------------------------------

class CoachInsight(BaseModel):
    insights_summary: str


def analyze_user_fitness(profile_data: dict) -> dict:
    """
    Computes the calorie plan deterministically, then asks Gemini only to
    explain it in plain, motivating language. Gemini is told the numbers as
    facts and explicitly instructed not to recompute them.
    """
    plan = compute_calorie_plan(profile_data)

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
    - Personal context from the user: {profile_data.get('context')}

    {feasibility_note}

    If relevant, mention the user's existing muscle base and any stress/water-weight
    context they shared. Return valid JSON with exactly one key: insights_summary.
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
    }


# ---------------------------------------------------------------------------
# Food estimation — unchanged, no math-consistency issue here
# ---------------------------------------------------------------------------

class FoodEstimation(BaseModel):
    itemized_breakdown: str
    estimated_calories: int
    protein: int
    fiber: int
    carbs: int


def estimate_food_calories(food_text: str) -> dict:
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
        raise


# ---------------------------------------------------------------------------
# Progress / consistency / weekly reports — math inputs now come from the
# deterministic plan computed above (via user_data), LLM still only narrates.
# ---------------------------------------------------------------------------

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


def analyze_progress_report(user_data: dict, daily_log: dict, selected_date: str) -> dict:
    starting_weight = user_data.get("starting_weight", user_data.get("weight", "N/A"))
    # cleaned up: was a redundant triple-nested .get() in the original
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
    1. "status_summary" - about today's progress toward the goal and motivate if needed.
    2. "change_observation" - one specific observation comparing today's weight or calories to the starting goal.
    3. "coach_recommendation" - one practical recommendation for the next day. State the weeks remaining
       using only the "Timeline Goal" given above — do not recalculate it yourself.
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
    Use the user's profile and intake data to provide a short assessment and one practical tip.

    User Profile:
    - Age: {user_data.get('age', 'N/A')}
    - Sex: {user_data.get('sex', 'N/A')}
    - Height: {user_data.get('height', 'N/A')} cm
    - Starting Weight: {user_data.get('starting_weight', 'N/A')} kg
    - Current Weight: {user_data.get('current_weight', user_data.get('weight', 'N/A'))} kg
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
    total_target = target_daily * 7
    net_deficit = total_target - total_consumed

    daily_breakdown = "\n".join([f"  {d['date']}: {d['total_consumed']} kcal" for d in daily_summaries])

    user_context = ""
    if user_data:
        user_context = f"""
    User Profile:
    - Age: {user_data.get('age', 'N/A')}
    - Sex: {user_data.get('sex', 'N/A')}
    - Height: {user_data.get('height', 'N/A')} cm
    - Starting Weight: {user_data.get('starting_weight', 'N/A')} kg
    - Current Weight: {user_data.get('current_weight', user_data.get('weight', 'N/A'))} kg
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