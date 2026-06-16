from fastapi import APIRouter, Request, Form,HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from services.firebase_service import save_user_profile, get_user_document
from services.gemini_service import analyze_user_fitness, estimate_food_calories
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


from datetime import datetime
from services.firebase_service import db # Import db directly if needed or add a service helper

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, uid: str, date: str = None):
    user_data = get_user_document(uid)
    if not user_data:
        return RedirectResponse(url="/")
    
    # Default to today's date if no date is picked from the calendar UI
    if not date:
        date = datetime.today().strftime('%Y-%m-%d')
        
    journey_status = {}
    daily_log = {"breakfast": 0, "lunch": 0, "dinner": 0, "total_consumed": 0, "balance": user_data.get("target_calories", 0)}
    
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
            daily_log["balance"] = user_data["target_calories"] - daily_log["total_consumed"]

    
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
        "calories": estimated_kcal
    }

    if log_doc.exists:
        # Document exists: Increment total and append the new entry to the array list
        log_ref.update({
            "total_consumed": firestore.Increment(estimated_kcal),
            "logs": firestore.ArrayUnion([new_log_entry])
        })
    else:
        # Document doesn't exist: Create a fresh record for the day
        log_data = {
            "date": date,
            "total_consumed": estimated_kcal,
            "logs": [new_log_entry]
        }
        log_ref.set(log_data)
        
    return RedirectResponse(url=f"/onboard/dashboard?uid={uid}&date={date}", status_code=303)