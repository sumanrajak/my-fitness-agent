from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from services.user_service import get_user
from services.tracking_service import get_daily_log, get_logs_in_range
from services.ai_service import analyze_weekly_report, analyze_consistency_review, analyze_progress_report

router = APIRouter(prefix="/onboard", tags=["Dashboard"])
templates = Jinja2Templates(directory="templates")

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, uid: str, date: str = None):
    user_data = get_user(uid)
    if not user_data:
        return RedirectResponse(url="/")
    
    if not date:
        date = datetime.today().strftime('%Y-%m-%d')
        
    journey_status = {}
    daily_log = {
        "breakfast": 0, "lunch": 0, "dinner": 0,
        "total_consumed": 0, "balance": user_data.get("target_calories", 0),
        "total_protein": 0, "total_fiber": 0, "total_carbs": 0,
        "weight": user_data.get("weight", 0),
        "activity_description": "", "steps": 0, "exercise_minutes": 0,
        "logs": []
    }
    
    if "journey_start_date" in user_data:
        start_dt = datetime.strptime(user_data["journey_start_date"], '%Y-%m-%d')
        current_dt = datetime.strptime(date, '%Y-%m-%d')
        
        days_diff = (current_dt - start_dt).days + 1
        if days_diff >= 1:
            journey_status["day_number"] = days_diff
            journey_status["week_number"] = ((days_diff - 1) // 7) + 1
        else:
            journey_status["day_number"] = "Before Start"
            journey_status["week_number"] = 0

        log_data = get_daily_log(uid, date)
        if log_data:
            daily_log = log_data
            daily_log.setdefault("weight", user_data.get("weight", 0))
            daily_log.setdefault("activity_description", "")
            daily_log.setdefault("steps", 0)
            daily_log.setdefault("exercise_minutes", 0)
            daily_log.setdefault("total_consumed", 0)
            daily_log.setdefault("logs", [])

            daily_log["balance"] = user_data["target_calories"] - daily_log.get("total_consumed", 0)
            logs = daily_log.get("logs", [])
            daily_log["total_protein"] = sum(item.get("protein", 0) for item in logs)
            daily_log["total_fiber"] = sum(item.get("fiber", 0) for item in logs)
            daily_log["total_carbs"] = sum(item.get("carbs", 0) for item in logs)
    
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"user": user_data, "journey_status": journey_status, "selected_date": date, "daily_log": daily_log}
    )

@router.get("/trends", response_class=HTMLResponse)
async def trends_page(request: Request, uid: str, days: int = 14):
    user_data = get_user(uid)
    if not user_data:
        return RedirectResponse(url="/")

    end_date = datetime.today()
    start_date = end_date - timedelta(days=days - 1)

    logs = get_logs_in_range(uid, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

    dates = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
    weight_values = []
    calorie_values = []
    activity_values = []
    chart_data = {d: {"weight": None, "calories": 0, "steps": 0, "exercise_minutes": 0} for d in dates}

    for data in logs:
        date_key = data.get("date")
        if date_key in chart_data:
            chart_data[date_key]["weight"] = data.get("weight")
            chart_data[date_key]["calories"] = data.get("total_consumed", 0)
            chart_data[date_key]["steps"] = data.get("steps", 0)
            chart_data[date_key]["exercise_minutes"] = data.get("exercise_minutes", 0)

    for d in dates:
        day = chart_data[d]
        weight_values.append(day["weight"] if day["weight"] is not None else 0)
        calorie_values.append(day["calories"])
        activity_values.append(day["steps"])

    return templates.TemplateResponse(
        name="trends.html",
        request=request,
        context={
            "user": user_data, "dates": dates, "weight_values": weight_values,
            "calorie_values": calorie_values, "activity_values": activity_values,
            "target_calories": user_data.get("target_calories", 0)
        }
    )

@router.get("/weekly-report", response_class=HTMLResponse)
async def weekly_report(request: Request, uid: str, start_date: str = None, end_date: str = None):
    user_data = get_user(uid)
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

    logs = get_logs_in_range(uid, start_date, end_date)
    
    dates_map = {}
    day_count = (end_dt - start_dt).days + 1
    for i in range(day_count):
        d = (start_dt + timedelta(days=i)).strftime('%Y-%m-%d')
        dates_map[d] = {"date": d, "total_consumed": 0, "logs_count": 0}

    total_consumed = 0
    for data in logs:
        d = data.get("date")
        if d in dates_map:
            dates_map[d]["total_consumed"] = data.get("total_consumed", 0)
            dates_map[d]["logs_count"] = len(data.get("logs", []))
            total_consumed += data.get("total_consumed", 0)

    daily_summaries = sorted(dates_map.values(), key=lambda x: x["date"])
    target_daily = user_data.get("target_calories", 0)
    total_target = target_daily * day_count
    net_deficit = total_target - total_consumed
    est_loss = net_deficit / 7700.0

    try:
        ai_analysis = analyze_weekly_report(
            daily_summaries=daily_summaries, target_daily=target_daily,
            total_consumed=total_consumed, estimated_weight_loss=est_loss, user_data=user_data
        )
        ai_analysis["total_consumed"] = total_consumed
        ai_analysis["total_target"] = total_target
        ai_analysis["net_deficit"] = net_deficit
        ai_analysis["estimated_weight_loss"] = round(est_loss, 2)
    except Exception as e:
        ai_analysis = {
            "status_summary": "Error in Analyzing Weekly Report",
            "coach_verdict": str(e), "detailed_insights": "",
            "total_consumed": total_consumed, "total_target": total_target,
            "net_deficit": net_deficit, "estimated_weight_loss": round(est_loss, 2)
        }

    return templates.TemplateResponse(
        name="weekly_report.html", request=request,
        context={"user": user_data, "start_date": start_date, "end_date": end_date, "daily_summaries": daily_summaries, "ai_analysis": ai_analysis}
    )

@router.get("/ai-review")
async def ai_review(uid: str):
    user_data = get_user(uid)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=6)).strftime('%Y-%m-%d')
    logs = get_logs_in_range(uid, start_date, end_date)

    recent_summaries = []
    for data in logs:
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

@router.get("/progress-review")
async def progress_review(uid: str, date: str = None):
    user_data = get_user(uid)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    if not date:
        date = datetime.today().strftime('%Y-%m-%d')

    log_data = get_daily_log(uid, date)
    daily_log = {
        "total_consumed": 0, "weight": user_data.get("weight", 0),
        "activity_description": "", "steps": 0, "exercise_minutes": 0, "logs": []
    }

    if log_data:
        daily_log = log_data
        daily_log.setdefault("weight", user_data.get("weight", 0))
        daily_log.setdefault("activity_description", "")
        daily_log.setdefault("steps", 0)
        daily_log.setdefault("exercise_minutes", 0)
        daily_log.setdefault("total_consumed", 0)
        daily_log.setdefault("logs", [])

    try:
        report = analyze_progress_report(user_data=user_data, daily_log=daily_log, selected_date=date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI progress review failed: {str(e)}")

    return {
        "status_summary": report.get("status_summary", "Unable to generate progress report."),
        "change_observation": report.get("change_observation", "No observation available."),
        "coach_recommendation": report.get("coach_recommendation", "Try logging your weight and activity before analyzing.")
    }
