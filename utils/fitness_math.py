import re
from datetime import datetime
from dateutil import parser as date_parser

KCAL_PER_KG_FAT = 7700

ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "lightly active": 1.375,
    "moderately active": 1.55,
    "very active": 1.725,
    "extra active": 1.9,
}

def get_activity_multiplier(activity_level: str) -> float:
    level = (activity_level or "").lower()
    for key, mult in ACTIVITY_MULTIPLIERS.items():
        if key in level:
            return mult
    return 1.375  # reasonable default

def calculate_bmr(age: float, sex: str, height_cm: float, weight_kg: float) -> float:
    """Mifflin-St Jeor BMR."""
    sex_constant = 5 if (sex or "").lower().startswith("m") else -161
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + sex_constant

def parse_days_remaining(timeline_str: str, today: datetime) -> tuple[int, bool]:
    timeline_str = (timeline_str or "").strip()
    try:
        target_date = date_parser.parse(timeline_str, fuzzy=True, default=today)
        if target_date.date() <= today.date():
            target_date = target_date.replace(year=target_date.year + 1)
        days = (target_date.date() - today.date()).days
        if days > 0:
            return days, True
    except (ValueError, OverflowError):
        pass

    match = re.search(r"(\d+)\s*week", timeline_str, re.IGNORECASE)
    if match: return int(match.group(1)) * 7, True
    match = re.search(r"(\d+)\s*month", timeline_str, re.IGNORECASE)
    if match: return int(match.group(1)) * 30, True
    match = re.search(r"(\d+)\s*day", timeline_str, re.IGNORECASE)
    if match: return int(match.group(1)), True

    return 84, False

def compute_calorie_plan(profile_data: dict) -> dict:
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
