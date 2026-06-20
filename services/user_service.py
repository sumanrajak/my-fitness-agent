from db.firestore import db

def get_user(uid: str) -> dict:
    doc = db.collection("users").document(uid).get()
    if doc.exists:
        return doc.to_dict()
    return None

def save_user(uid: str, profile_data: dict):
    db.collection("users").document(uid).set(profile_data, merge=True)

def log_reanalysis_history(uid: str, log_data: dict):
    try:
        db.collection("users").document(uid).collection("reanalyze_logs").add(log_data)
    except Exception as e:
        print(f"Error logging history: {e}")

def get_reanalysis_history(uid: str) -> list:
    try:
        from google.cloud import firestore
        docs = db.collection("users").document(uid).collection("reanalyze_logs").order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
        return [d.to_dict() for d in docs]
    except Exception:
        return []
