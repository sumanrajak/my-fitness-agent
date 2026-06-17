import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from config.settings import settings
from services.firebase_service import save_user_profile, get_user_document, db
from services.gemini_service import analyze_user_fitness, estimate_food_calories, analyze_weekly_report, analyze_consistency_review
router = APIRouter(prefix="/onboard", tags=["Onboarding & Dashboard"])
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
    activity_level: str = Form(...),
    context: str = Form(...),
    timeline: str = Form(...)
):
    # Pack user inputs
    profile_data = {
        "uid": uid,
        "email": email,
        "age": age,
        "sex": sex,
        "height": height,
        "weight": weight,
        "activity_level": activity_level,
        "context": context,
        "timeline": timeline
    }

    # Pass data to Gemini AI Agent for calorie and context analysis
    ai_analysis = analyze_user_fitness(profile_data)

    # Merge AI analysis back into the profile payload
    profile_data["maintenance_calories"] = ai_analysis["maintenance_calories"]
    profile_data["target_calories"] = ai_analysis["target_calories"]
    profile_data["insights_summary"] = ai_analysis["insights_summary"]

    # Save to Firestore
    save_user_profile(uid, profile_data)

    # Redirect to dashboard
    return RedirectResponse(url=f"/onboard/dashboard?uid={uid}", status_code=303)



@router.post("/start-journey")
async def start_journey(uid: str = Form(...), start_date: str = Form(...)):
    """
    Saves the official start date of the fitness journey to the user's profile.
    """
    # Fallback to current date if something goes wrong
    if not start_date:
        start_date = datetime.today().strftime('%Y-%m-%d')
        
    update_data = {
        "journey_start_date": start_date
    }
    
    # Merge this into the existing Firestore document
    save_user_profile(uid, update_data)
    
    return RedirectResponse(url=f"/onboard/dashboard?uid={uid}", status_code=303)

@router.get("/reanalysis", response_class=HTMLResponse)
async def reanalysis_page(request: Request, uid: str):
    user_data = get_user_document(uid)
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
            "button_label": "Update Goals"
        }
    )

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, uid: str, date: str = None):
    user_data = get_user_document(uid)
    if not user_data:
        return RedirectResponse(url="/")
    
    # Default to today's date if no date is picked from the calendar UI
    if not date:
        date = datetime.today().strftime('%Y-%m-%d')
        
    journey_status = {}
    daily_log = {
        "breakfast": 0,
        "lunch": 0,
        "dinner": 0,
        "total_consumed": 0,
        "balance": user_data.get("target_calories", 0),
        "total_protein": 0,
        "total_fiber": 0,
        "total_carbs": 0,
        "logs": []
    }
    
    # If the user has officially started their journey
    if "journey_start_date" in user_data:
        start_dt = datetime.strptime(user_data["journey_start_date"], '%Y-%m-%d')
        current_dt = datetime.strptime(date, '%Y-%m-%d')
        
        # Calculate current Day and Week
        days_diff = (current_dt - start_dt).days + 1
        if days_diff >= 1:
            journey_status["day_number"] = days_diff
            journey_status["week_number"] = ((days_diff - 1) // 7) + 1
        else:
            journey_status["day_number"] = "Before Start"
            journey_status["week_number"] = 0

        # Fetch tracking data for the selected date from the subcollection
        log_ref = db.collection("users").document(uid).collection("daily_tracker").document(date)
        log_doc = log_ref.get()
        
        if log_doc.exists:
            daily_log = log_doc.to_dict()
            # Calculate remaining balance dynamically
            daily_log["balance"] = user_data["target_calories"] - daily_log.get("total_consumed", 0)
            # Summarize macros for the selected date
            logs = daily_log.get("logs", [])
            daily_log["total_protein"] = sum(item.get("protein", 0) for item in logs)
            daily_log["total_fiber"] = sum(item.get("fiber", 0) for item in logs)
            daily_log["total_carbs"] = sum(item.get("carbs", 0) for item in logs)

    
    return templates.TemplateResponse(
    request=request,
    name="dashboard.html",
    context={
        "user": user_data, 
        "journey_status": journey_status,
        "selected_date": date,
        "daily_log": daily_log
    }
)

@router.get("/weekly-report", response_class=HTMLResponse)
async def weekly_report(request: Request, uid: str, start_date: str = None, end_date: str = None):
    user_data = get_user_document(uid)
    if not user_data:
        return RedirectResponse(url="/")
    
    if not end_date:
        end_date = datetime.today().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=6)).strftime('%Y-%m-%d')

    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    if end_dt < start_dt:
        start_dt, end_dt = end_dt, start_dt
        start_date, end_date = end_date, start_date

    # Fetch logs for the selected date range
    logs_ref = db.collection("users").document(uid).collection("daily_tracker")
    docs = logs_ref.where("date", ">=", start_date).where("date", "<=", end_date).stream()
    
    # Initialize map to ensure all days are represented
    dates_map = {}
    day_count = (end_dt - start_dt).days + 1
    for i in range(day_count):
        d = (start_dt + timedelta(days=i)).strftime('%Y-%m-%d')
        dates_map[d] = {"date": d, "total_consumed": 0, "logs_count": 0}

    total_consumed = 0
    for doc in docs:
        data = doc.to_dict()
        d = data.get("date")
        if d in dates_map:
            dates_map[d]["total_consumed"] = data.get("total_consumed", 0)
            dates_map[d]["logs_count"] = len(data.get("logs", []))
            total_consumed += data.get("total_consumed", 0)

    daily_summaries = sorted(dates_map.values(), key=lambda x: x["date"])
    target_daily = user_data.get("target_calories", 0)
    total_target = target_daily * day_count
    net_deficit = total_target - total_consumed
    est_loss = net_deficit / 7700.0  # Approx 7700 kcal deficit = 1kg

    # LLM Call for Weekly Analysis using the dedicated service function
    try:
        ai_analysis = analyze_weekly_report(
            daily_summaries=daily_summaries,
            target_daily=target_daily,
            total_consumed=total_consumed,
            estimated_weight_loss=est_loss,
            user_data=user_data
        )
        # Add calculated metrics to the analysis
        ai_analysis["total_consumed"] = total_consumed
        ai_analysis["total_target"] = total_target
        ai_analysis["net_deficit"] = net_deficit
        ai_analysis["estimated_weight_loss"] = round(est_loss, 2)
    except Exception as e:
        print("LLM Error:", e)
        ai_analysis = {
            "status_summary": "Error in Analyzing Weekly Report",
            "coach_verdict": e,
            "detailed_insights": "",
            "total_consumed": total_consumed,
            "total_target": total_target,
            "net_deficit": net_deficit,
            "estimated_weight_loss": round(est_loss, 2)
        }

    return templates.TemplateResponse(
        name="weekly_report.html",
        request=request,
        context={
            "user": user_data,
            "start_date": start_date,
            "end_date": end_date,
            "daily_summaries": daily_summaries,
            "ai_analysis": ai_analysis
        }
    )

@router.post("/log-calories")
async def log_calories(
    uid: str = Form(...),
    date: str = Form(...),
    meal_type: str = Form(...),        # "Breakfast", "Lunch", or "Dinner"
    food_description: str = Form(...)  # "2 parathas with curd"
):
    # 1. Get the AI Estimation
    try:
        ai_result = estimate_food_calories(food_description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Calorie Estimation failed: {str(e)}")
        
    estimated_kcal = ai_result["estimated_calories"]
    breakdown = ai_result["itemized_breakdown"]

    # 2. Reference the specific day document
    log_ref = db.collection("users").document(uid).collection("daily_tracker").document(date)
    log_doc = log_ref.get()

    from google.cloud import firestore
    
    new_log_entry = {
        "timestamp": datetime.now().strftime("%H:%M"),
        "meal_type": meal_type,
        "input_text": food_description,
        "breakdown": breakdown,
        "calories": estimated_kcal,
        "protein": ai_result.get("protein", 0),
        "fiber": ai_result.get("fiber", 0),
        "carbs": ai_result.get("carbs", 0)
    }

    if log_doc.exists:
        # Document exists: Increment totals and append the new entry to the array list
        log_ref.update({
            "total_consumed": firestore.Increment(estimated_kcal),
            "total_protein": firestore.Increment(ai_result.get("protein", 0)),
            "total_fiber": firestore.Increment(ai_result.get("fiber", 0)),
            "total_carbs": firestore.Increment(ai_result.get("carbs", 0)),
            "logs": firestore.ArrayUnion([new_log_entry])
        })
    else:
        # Document doesn't exist: Create a fresh record for the day
        log_data = {
            "date": date,
            "total_consumed": estimated_kcal,
            "total_protein": ai_result.get("protein", 0),
            "total_fiber": ai_result.get("fiber", 0),
            "total_carbs": ai_result.get("carbs", 0),
            "logs": [new_log_entry]
        }
        log_ref.set(log_data)
        
    return RedirectResponse(url=f"/onboard/dashboard?uid={uid}&date={date}", status_code=303)

@router.get("/ai-review")
async def ai_review(uid: str):
    user_data = get_user_document(uid)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=6)).strftime('%Y-%m-%d')
    logs_ref = db.collection("users").document(uid).collection("daily_tracker")
    docs = logs_ref.where("date", ">=", start_date).where("date", "<=", end_date).stream()

    recent_summaries = []
    for doc in docs:
        data = doc.to_dict()
        recent_summaries.append({
            "date": data.get("date"),
            "total_consumed": data.get("total_consumed", 0),
            "logs_count": len(data.get("logs", []))
        })

    try:
        review = analyze_consistency_review(user_data=user_data, recent_summaries=recent_summaries)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI consistency review failed: {str(e)}")

    return {
        "status_evaluation": review.get("status_evaluation", "Unable to evaluate consistency."),
        "actionable_tip": review.get("actionable_tip", "Keep logging regularly and stay consistent with meal balance.")
    }
