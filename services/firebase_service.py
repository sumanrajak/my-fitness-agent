import os
import firebase_admin
from firebase_admin import credentials, firestore, auth  # Added auth here

from config import settings

# Initialize Firebase Admin if not already initialized
if not firebase_admin._apps:
    # Check multiple possible paths for credentials file
    creds_path = settings.FIREBASE_CREDENTIALS_PATH
    possible_paths = [
        "/etc/secrets/serviceAccountKey.json",  # Render's secret directory
        "/etc/secrets/config/serviceAccountKey.json",  # Alternate Render path
        creds_path,  # Default/local path
    ]
    
    # Find the first path that exists
    for path in possible_paths:
        if os.path.exists(path):
            creds_path = path
            break
    
    cred = credentials.Certificate(creds_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def get_user_document(uid: str):
    """Fetch user document from Firestore."""
    user_ref = db.collection("users").document(uid)
    doc = user_ref.get()
    print(doc.to_dict())
    if doc.exists:
        return doc.to_dict()
    return None

def save_user_profile(uid: str, profile_data: dict):
    """Save or update user profile and AI calculations."""
    user_ref = db.collection("users").document(uid)
    user_ref.set(profile_data, merge=True)