import firebase_admin
from firebase_admin import credentials, firestore, auth  # Added auth here

from config import settings

# Initialize Firebase Admin if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def get_user_document(uid: str):
    """Fetch user document from Firestore."""
    user_ref = db.collection("users").document(uid)
    doc = user_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None

def save_user_profile(uid: str, profile_data: dict):
    """Save or update user profile and AI calculations."""
    user_ref = db.collection("users").document(uid)
    user_ref.set(profile_data, merge=True)