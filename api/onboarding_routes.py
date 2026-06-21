from datetime import datetime
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from services.user_service import get_user, save_user, log_reanalysis_history, get_reanalysis_history
from services.ai_service import analyze_user_fitness

router = APIRouter(prefix="/onboard", tags=["Onboarding"])
templates = Jinja2Templates(directory="templates")

@router.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page(request: Request, uid: str, email: str = ""):
    return templates.TemplateResponse(name="onboarding.html", request=request, context={"uid": uid, "email": email})

@router.post("/submit")
async def handle_onboarding_submit(
    uid: str = Form(...),
    email: str = Form(...),
    age: int = Form(...),
    sex: str = Form(...),
    height: float = Form(...),
    weight: float = Form(...),
    target_weight: float = Form(...),
    activity_level: str = Form(...),
    context: str = Form(...),
    timeline: str = Form(...)
):
    profile_data = {
        "uid": uid,
        "email": email,
        "age": age,
        "sex": sex,
        "height": height,
        "weight": weight,
        "target_weight": target_weight,
        "activity_level": activity_level,
        "context": context,
        "timeline": timeline
    }

    existing_user = get_user(uid)
    profile_data["starting_weight"] = existing_user.get("starting_weight") if existing_user and existing_user.get("starting_weight") else weight
    profile_data["current_weight"] = weight

    ai_analysis = analyze_user_fitness(profile_data)

    if existing_user and existing_user.get("starting_weight"):
        reanalysis_update = {
            "current_weight": weight,
            "target_weight": target_weight,
            "activity_level": activity_level,
            "context": context,
            "timeline": timeline,
            "maintenance_calories": ai_analysis.get("maintenance_calories"),
            "target_calories": ai_analysis.get("target_calories"),
            "daily_deficit": ai_analysis.get("daily_deficit"),
            "insights_summary": ai_analysis.get("insights_summary"),
            "weight_predictions": ai_analysis.get("weight_predictions"),
            "last_reanalysis_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "reanalyze_insights": ai_analysis
        }
        save_user(uid, reanalysis_update)

        log_data = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "current_weight": weight,
            "input": {
                "age": age,
                "sex": sex,
                "height": height,
                "target_weight": target_weight,
                "activity_level": activity_level,
                "timeline": timeline,
                "context": context
            },
            "ai_insights": ai_analysis
        }
        log_reanalysis_history(uid, log_data)
        return RedirectResponse(url=f"/onboard/dashboard?uid={uid}", status_code=303)

    profile_data["starting_weight"] = weight
    profile_data["current_weight"] = weight
    profile_data["maintenance_calories"] = ai_analysis.get("maintenance_calories")
    profile_data["target_calories"] = ai_analysis.get("target_calories")
    profile_data["daily_deficit"] = ai_analysis.get("daily_deficit")
    profile_data["insights_summary"] = ai_analysis.get("insights_summary")
    profile_data["weight_predictions"] = ai_analysis.get("weight_predictions")

    save_user(uid, profile_data)
    return RedirectResponse(url=f"/onboard/dashboard?uid={uid}", status_code=303)

@router.post("/start-journey")
async def start_journey(uid: str = Form(...), start_date: str = Form(...)):
    if not start_date:
        start_date = datetime.today().strftime('%Y-%m-%d')

    update_data = {"journey_start_date": start_date}

    existing_user = get_user(uid)
    if existing_user and not existing_user.get("starting_weight"):
        update_data["starting_weight"] = existing_user.get("weight")

    save_user(uid, update_data)
    return RedirectResponse(url=f"/onboard/dashboard?uid={uid}", status_code=303)

@router.get("/reanalysis", response_class=HTMLResponse)
async def reanalysis_page(request: Request, uid: str):
    user_data = get_user(uid)
    if not user_data:
        return RedirectResponse(url="/")

    return templates.TemplateResponse(
        name="onboarding.html",
        request=request,
        context={
            "uid": uid,
            "email": user_data.get("email", ""),
            "age": user_data.get("age", ""),
            "sex": user_data.get("sex", ""),
            "height": user_data.get("height", ""),
            "weight": user_data.get("weight", ""),
            "activity_level": user_data.get("activity_level", ""),
            "context": user_data.get("context", ""),
            "timeline": user_data.get("timeline", ""),
            "title": "Reanalyze Your Goals",
            "button_label": "Update Goals",
            "target_weight": user_data.get("target_weight", ""),
        }
    )

@router.get("/reanalysis-history", response_class=HTMLResponse)
async def reanalysis_history(request: Request, uid: str):
    user_data = get_user(uid)
    if not user_data:
        return RedirectResponse(url="/")

    logs = get_reanalysis_history(uid)

    return templates.TemplateResponse(
        name="reanalysis_history.html",
        request=request,
        context={"user": user_data, "logs": logs}
    )
