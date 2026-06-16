import requests
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from services.firebase_service import get_user_document, auth as firebase_auth

router = APIRouter(prefix="/auth", tags=["Authentication"])
templates = Jinja2Templates(directory="templates")

# Firebase Auth REST API endpoints require your Web API Key.
# You can find this in your Firebase Project Settings -> General -> Web API Key.
# Drop this into your .env as FIREBASE_WEB_API_KEY
import os
FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY", "AIzaSyBJKWl3oh0i0DUAP3CSgZFW0vLRzqCQVwQ")

@router.post("/register")
async def register_user(email: str = Form(...), password: str = Form(...)):
    """
    Creates a new user account in Firebase Auth.
    """
    try:
        user = firebase_auth.create_user(
            email=email,
            password=password
        )
        # Successfully created user. Now redirect straight to onboarding.
        return RedirectResponse(url=f"/onboard/onboarding?uid={user.uid}&email={email}", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

@router.post("/login")
async def login_user(email: str = Form(...), password: str = Form(...)):
    """
    Authenticates user credentials using Firebase REST API.
    """
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    
    response = requests.post(url, json=payload)
    res_data = response.json()
    
    if response.status_code != 200:
        error_msg = res_data.get("error", {}).get("message", "Authentication Failed")
        raise HTTPException(status_code=401, detail=error_msg)
    
    uid = res_data.get("localId")
    
    # Check if this user already has an onboarding record in Firestore
    user_data = get_user_document(uid)
    
    if user_data:
        # Returning user goes straight to Dashboard
        return RedirectResponse(url=f"/onboard/dashboard?uid={uid}", status_code=303)
    else:
        # New user who didn't onboard yet goes to onboarding setup
        return RedirectResponse(url=f"/onboard/onboarding?uid={uid}&email={email}", status_code=303)