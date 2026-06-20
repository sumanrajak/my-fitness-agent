from datetime import datetime
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import RedirectResponse
from services.tracking_service import save_daily_checkin, add_meal_log, get_daily_log, update_daily_log_raw
from services.ai_service import estimate_food_calories

router = APIRouter(prefix="/onboard", tags=["Tracking"])

@router.post("/save-daily-log")
async def save_daily_log(
    uid: str = Form(...),
    date: str = Form(...),
    weight: float = Form(...),
    activity_description: str = Form(""),
    steps: int = Form(0),
    exercise_minutes: int = Form(0),
    went_to_gym: bool = Form(False)
):
    update_data = {
        "date": date,
        "weight": weight,
        "activity_description": activity_description,
        "steps": steps,
        "exercise_minutes": exercise_minutes,
        "went_to_gym": went_to_gym,
    }
    save_daily_checkin(uid, date, update_data)
    return RedirectResponse(url=f"/onboard/dashboard?uid={uid}&date={date}", status_code=303)

@router.post("/log-calories")
async def log_calories(
    uid: str = Form(...),
    date: str = Form(...),
    meal_type: str = Form(...),
    food_description: str = Form(...)
):
    try:
        ai_result = estimate_food_calories(food_description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Calorie Estimation failed: {str(e)}")
        
    estimated_kcal = ai_result["estimated_calories"]
    breakdown = ai_result["itemized_breakdown"]

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

    add_meal_log(uid, date, ai_result, new_log_entry)
    return RedirectResponse(url=f"/onboard/dashboard?uid={uid}&date={date}", status_code=303)

@router.post("/edit-log-item")
async def edit_log_item(
    uid: str = Form(...),
    date: str = Form(...),
    index: int = Form(...),
    calories: int = Form(...),
    input_text: str = Form(...)
):
    log_data = get_daily_log(uid, date)
    if not log_data:
        raise HTTPException(status_code=404, detail="Daily log not found")

    logs = log_data.get("logs", [])
    if index < 0 or index >= len(logs):
        raise HTTPException(status_code=400, detail="Invalid log item index")

    logs[index]["calories"] = calories
    logs[index]["input_text"] = input_text

    total_consumed = sum(item.get("calories", 0) for item in logs)
    total_protein = sum(item.get("protein", 0) for item in logs)
    total_fiber = sum(item.get("fiber", 0) for item in logs)
    total_carbs = sum(item.get("carbs", 0) for item in logs)

    update_daily_log_raw(uid, date, {
        "logs": logs,
        "total_consumed": total_consumed,
        "total_protein": total_protein,
        "total_fiber": total_fiber,
        "total_carbs": total_carbs
    })

    return RedirectResponse(url=f"/onboard/dashboard?uid={uid}&date={date}", status_code=303)

@router.post("/delete-log-item")
async def delete_log_item(
    uid: str = Form(...),
    date: str = Form(...),
    index: int = Form(...)
):
    log_data = get_daily_log(uid, date)
    if not log_data:
        raise HTTPException(status_code=404, detail="Daily log not found")

    logs = log_data.get("logs", [])
    if index < 0 or index >= len(logs):
        raise HTTPException(status_code=400, detail="Invalid log item index")

    logs.pop(index)

    total_consumed = sum(item.get("calories", 0) for item in logs)
    total_protein = sum(item.get("protein", 0) for item in logs)
    total_fiber = sum(item.get("fiber", 0) for item in logs)
    total_carbs = sum(item.get("carbs", 0) for item in logs)

    update_daily_log_raw(uid, date, {
        "logs": logs,
        "total_consumed": total_consumed,
        "total_protein": total_protein,
        "total_fiber": total_fiber,
        "total_carbs": total_carbs
    })

    return RedirectResponse(url=f"/onboard/dashboard?uid={uid}&date={date}", status_code=303)
