import os
import json
import firebase_admin
from firebase_admin import credentials, firestore, auth
from core.config import settings

if not firebase_admin._apps:
    # Cloud deployment: load credentials from environment variable (JSON string)
    firebase_creds_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if firebase_creds_json:
        cred_dict = json.loads(firebase_creds_json)
        cred = credentials.Certificate(cred_dict)
    else:
        # Local development: load from file path
        creds_path = settings.FIREBASE_CREDENTIALS_PATH
        possible_paths = [
            "/etc/secrets/serviceAccountKey.json",
            "/etc/secrets/config/serviceAccountKey.json",
            creds_path,
        ]
        for path in possible_paths:
            if os.path.exists(path):
                creds_path = path
                break
        cred = credentials.Certificate(creds_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

