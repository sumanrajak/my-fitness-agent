import os
import requests
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import RedirectResponse
from services.user_service import get_user
from firebase_admin import auth as firebase_auth
from core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register")
async def register_user(email: str = Form(...), password: str = Form(...)):
    try:
        user = firebase_auth.create_user(
            email=email,
            password=password
        )
        return RedirectResponse(url=f"/onboard/onboarding?uid={user.uid}&email={email}", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

@router.post("/login")
async def login_user(email: str = Form(...), password: str = Form(...)):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={settings.FIREBASE_WEB_API_KEY}"
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
    
    user_data = get_user(uid)
    
    if user_data:
        return RedirectResponse(url=f"/onboard/dashboard?uid={uid}", status_code=303)
    else:
        return RedirectResponse(url=f"/onboard/onboarding?uid={uid}&email={email}", status_code=303)
