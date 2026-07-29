from db.firestore import db
from datetime import datetime, timedelta
from google.cloud import firestore

def get_daily_log(uid: str, date: str) -> dict:
    log_doc = db.collection("users").document(uid).collection("daily_tracker").document(date).get()
    if log_doc.exists:
        return log_doc.to_dict()
    return None

def save_daily_checkin(uid: str, date: str, update_data: dict):
    log_ref = db.collection("users").document(uid).collection("daily_tracker").document(date)
    log_doc = log_ref.get()
    if log_doc.exists:
        log_ref.set(update_data, merge=True)
    else:
        update_data.update({
            "total_consumed": 0,
            "total_protein": 0,
            "total_fiber": 0,
            "total_carbs": 0,
            "logs": []
        })
        log_ref.set(update_data)

def add_meal_log(uid: str, date: str, meal_data: dict, log_entry: dict):
    log_ref = db.collection("users").document(uid).collection("daily_tracker").document(date)
    log_doc = log_ref.get()
    if log_doc.exists:
        log_ref.update({
            "total_consumed": firestore.Increment(meal_data["estimated_calories"]),
            "total_protein": firestore.Increment(meal_data["protein"]),
            "total_fiber": firestore.Increment(meal_data["fiber"]),
            "total_carbs": firestore.Increment(meal_data["carbs"]),
            "logs": firestore.ArrayUnion([log_entry])
        })
    else:
        log_data = {
            "date": date,
            "total_consumed": meal_data["estimated_calories"],
            "total_protein": meal_data["protein"],
            "total_fiber": meal_data["fiber"],
            "total_carbs": meal_data["carbs"],
            "logs": [log_entry]
        }
        log_ref.set(log_data)

def get_logs_in_range(uid: str, start_date: str, end_date: str) -> list:
    docs = db.collection("users").document(uid).collection("daily_tracker")\
             .where("date", ">=", start_date).where("date", "<=", end_date).stream()
    return [d.to_dict() for d in docs]


def get_weight_range_stats(uid: str) -> dict:
    docs = db.collection("users").document(uid).collection("daily_tracker").stream()
    weights = []
    weight_entries = []

    for doc in docs:
        data = doc.to_dict() or {}
        weight = data.get("weight")
        if weight is None:
            continue
        try:
            numeric_weight = float(weight)
        except (TypeError, ValueError):
            continue

        weights.append(numeric_weight)
        weight_entries.append({
            "date": data.get("date"),
            "weight": numeric_weight,
        })

    if not weights:
        return {
            "lowest_weight": None,
            "highest_weight": None,
            "difference": None,
            "weight_entries_count": 0,
            "lowest_weight_date": None,
            "highest_weight_date": None,
        }

    lowest_entry = min(weight_entries, key=lambda item: item["weight"])
    highest_entry = max(weight_entries, key=lambda item: item["weight"])

    return {
        "lowest_weight": round(lowest_entry["weight"], 1),
        "highest_weight": round(highest_entry["weight"], 1),
        "difference": round(highest_entry["weight"] - lowest_entry["weight"], 1),
        "weight_entries_count": len(weight_entries),
        "lowest_weight_date": lowest_entry.get("date"),
        "highest_weight_date": highest_entry.get("date"),
    }


def update_daily_log_raw(uid: str, date: str, data: dict):
    db.collection("users").document(uid).collection("daily_tracker").document(date).update(data)
