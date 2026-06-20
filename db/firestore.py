import os
import firebase_admin
from firebase_admin import credentials, firestore, auth
from core.config import settings

if not firebase_admin._apps:
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
