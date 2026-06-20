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
            "total_consumed": firestore.Increment(meal_data["calories"]),
            "total_protein": firestore.Increment(meal_data["protein"]),
            "total_fiber": firestore.Increment(meal_data["fiber"]),
            "total_carbs": firestore.Increment(meal_data["carbs"]),
            "logs": firestore.ArrayUnion([log_entry])
        })
    else:
        log_data = {
            "date": date,
            "total_consumed": meal_data["calories"],
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

def update_daily_log_raw(uid: str, date: str, data: dict):
    db.collection("users").document(uid).collection("daily_tracker").document(date).update(data)
