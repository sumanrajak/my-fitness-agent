import os
import requests
from datetime import timedelta
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from services.user_service import get_user
from firebase_admin import auth as firebase_auth
from core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

def _set_fitness_session(response, id_token: str, request: Request):
    session_cookie = firebase_auth.create_session_cookie(
        id_token, expires_in=timedelta(days=5)
    )
    response.set_cookie(
        key="fitness_session",
        value=session_cookie,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=5 * 24 * 60 * 60,
    )
    return response

@router.post("/register")
async def register_user(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        user = firebase_auth.create_user(
            email=email,
            password=password
        )
        sign_in = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={settings.FIREBASE_WEB_API_KEY}",
            json={"email": email, "password": password, "returnSecureToken": True},
            timeout=15,
        )
        if sign_in.status_code != 200:
            print(f"New user session sign-in failed: {sign_in.status_code}")
            return RedirectResponse(url=f"/onboard/onboarding?uid={user.uid}&email={email}", status_code=303)
        response = RedirectResponse(url=f"/onboard/onboarding?uid={user.uid}&email={email}", status_code=303)
        return _set_fitness_session(response, sign_in.json()["idToken"], request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

@router.post("/login")
async def login_user(request: Request, email: str = Form(...), password: str = Form(...)):
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
        response = RedirectResponse(url=f"/onboard/dashboard?uid={uid}", status_code=303)
    else:
        response = RedirectResponse(url=f"/onboard/onboarding?uid={uid}&email={email}", status_code=303)
    return _set_fitness_session(response, res_data["idToken"], request)

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("fitness_session")
    return response
