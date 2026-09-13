from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from services.user_service import get_user
from services.tracking_service import get_daily_log, get_logs_in_range, get_weight_range_stats
from services.ai_service import analyze_weekly_report, analyze_consistency_review, analyze_progress_report, generate_craving_support
from services.ai_service import analyze_weekly_report, analyze_consistency_review, analyze_progress_report, generate_craving_support, recommend_next_meal

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
    
    # Format the prediction dates if they exist
    if "weight_predictions" in user_data:
        for pt in user_data["weight_predictions"]:
            pt_date_str = pt.get("date")
            if pt_date_str:
                try:
                    pt_dt = datetime.strptime(pt_date_str, '%Y-%m-%d')
                    pt["formatted_date"] = pt_dt.strftime('%b %d')
                except Exception:
                    pt["formatted_date"] = pt_date_str
            else:
                pt["formatted_date"] = None

    weight_stats = get_weight_range_stats(uid)

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

        # Determine the active week based on the selected date and the stored prediction dates
        active_week_num = None
        if "weight_predictions" in user_data:
            predictions = user_data["weight_predictions"]
            try:
                selected_dt = datetime.strptime(date, '%Y-%m-%d')
                sorted_preds = sorted(predictions, key=lambda x: int(x.get("week", 0)))
                for i, pt in enumerate(sorted_preds):
                    pt_date_str = pt.get("date")
                    if not pt_date_str:
                        continue
                    
                    pt_dt = datetime.strptime(pt_date_str, '%Y-%m-%d')
                    
                    # Determine active week
                    next_pt_dt = None
                    if i + 1 < len(sorted_preds):
                        next_date_str = sorted_preds[i+1].get("date")
                        if next_date_str:
                            next_pt_dt = datetime.strptime(next_date_str, '%Y-%m-%d')
                    
                    if next_pt_dt:
                        if pt_dt <= selected_dt < next_pt_dt:
                            active_week_num = int(pt.get("week", 0))
                    else:
                        if pt_dt <= selected_dt:
                            active_week_num = int(pt.get("week", 0))
                
                if active_week_num is None and sorted_preds:
                    first_date_str = sorted_preds[0].get("date")
                    if first_date_str:
                        first_dt = datetime.strptime(first_date_str, '%Y-%m-%d')
                        if selected_dt < first_dt:
                            active_week_num = int(sorted_preds[0].get("week", 0))
            except Exception as e:
                print(f"Error determining active week: {e}")
        
        journey_status["active_week_num"] = active_week_num

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
        context={
            "user": user_data,
            "journey_status": journey_status,
            "selected_date": date,
            "daily_log": daily_log,
            "weight_stats": weight_stats
        }
    )

@router.post("/update-target-calories")
async def update_target_calories(uid: str = Form(...), target_calories: int = Form(...), date: str = Form(None)):
    from services.user_service import save_user
    save_user(uid, {"target_calories": target_calories})
    url = f"/onboard/dashboard?uid={uid}"
    if date:
        url += f"&date={date}"
    return RedirectResponse(url=url, status_code=303)

@router.get("/trends", response_class=HTMLResponse)
async def trends_page(request: Request, uid: str, days: int = 14, start_date: str = None, end_date: str = None):
    user_data = get_user(uid)
    if not user_data:
        return RedirectResponse(url="/")

    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            if end_dt < start_dt:
                start_dt, end_dt = end_dt, start_dt
                start_date, end_date = end_date, start_date
            days = (end_dt - start_dt).days + 1
        except ValueError:
            end_dt = datetime.today()
            start_dt = end_dt - timedelta(days=days - 1)
            start_date = start_dt.strftime('%Y-%m-%d')
            end_date = end_dt.strftime('%Y-%m-%d')
    else:
        end_dt = datetime.today()
        start_dt = end_dt - timedelta(days=days - 1)
        start_date = start_dt.strftime('%Y-%m-%d')
        end_date = end_dt.strftime('%Y-%m-%d')

    logs = get_logs_in_range(uid, start_date, end_date)

    dates = [(start_dt + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
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

    # Fetch all logs in the selected date range months for the gym calendar
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        gym_start = start_dt.replace(day=1).strftime('%Y-%m-%d')
        # last day of end_dt's month
        next_month = end_dt.replace(day=28) + timedelta(days=4)
        gym_end = (next_month - timedelta(days=next_month.day)).strftime('%Y-%m-%d')
    except Exception:
        now = datetime.today()
        gym_start = now.replace(day=1).strftime('%Y-%m-%d')
        gym_end = now.strftime('%Y-%m-%d')

    gym_logs = get_logs_in_range(uid, gym_start, gym_end)
    gym_dates = [log["date"] for log in gym_logs if log.get("went_to_gym")]

    return templates.TemplateResponse(
        name="trends.html",
        request=request,
        context={
            "user": user_data, "dates": dates, "weight_values": weight_values,
            "calorie_values": calorie_values, "activity_values": activity_values,
            "target_calories": user_data.get("target_calories", 0),
            "gym_dates": gym_dates,
            "start_date": start_date,
            "end_date": end_date
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
    weight_stats = get_weight_range_stats(uid)
    
    dates_map = {}
    day_count = (end_dt - start_dt).days + 1
    for i in range(day_count):
        d = (start_dt + timedelta(days=i)).strftime('%Y-%m-%d')
        dates_map[d] = {
            "date": d,
            "total_consumed": 0,
            "logs_count": 0,
            "weight": None,
            "total_protein": 0,
            "steps": 0
        }

    total_consumed = 0
    for data in logs:
        d = data.get("date")
        if d in dates_map:
            dates_map[d]["total_consumed"] = data.get("total_consumed", 0)
            dates_map[d]["logs_count"] = len(data.get("logs", []))
            dates_map[d]["weight"] = data.get("weight")
            dates_map[d]["steps"] = data.get("steps", 0)
            
            # Sum protein from itemized food logs for that day
            day_logs = data.get("logs", [])
            dates_map[d]["total_protein"] = sum(item.get("protein", 0) for item in day_logs)
            
            total_consumed += data.get("total_consumed", 0)

    daily_summaries = sorted(dates_map.values(), key=lambda x: x["date"])
    target_daily = user_data.get("target_calories", 0)
    total_target = target_daily * day_count
    net_deficit = total_target - total_consumed
    est_loss = net_deficit / 7700.0

    try:
        ai_analysis = analyze_weekly_report(
            daily_summaries=daily_summaries, target_daily=target_daily,
            total_consumed=total_consumed, estimated_weight_loss=est_loss, user_data=user_data,
            weight_stats=weight_stats
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

@router.get("/craving-support")
async def craving_support(uid: str, note: str = ""):
    user_data = get_user(uid)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    if "suman" not in user_data.get("email", "").lower():
        raise HTTPException(status_code=403, detail="Craving support is not enabled for this account")

    today = datetime.today()
    start_date = (today - timedelta(days=6)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    weekly_progress = get_logs_in_range(uid, start_date, end_date)
    weekly_progress.sort(key=lambda entry: entry.get("date", ""))

    quit_at = datetime.strptime("2026-09-13 02:00:00", "%Y-%m-%d %H:%M:%S")
    elapsed_seconds = max(0, int((today - quit_at).total_seconds()))
    smoke_free_days = elapsed_seconds // 86400
    smoke_free_hours = elapsed_seconds // 3600
    money_saved = int((elapsed_seconds / 86400) * 12 * 20)
    next_10_days_savings = 10 * 12 * 20
    support = generate_craving_support(
        user_data=user_data,
        weekly_progress=weekly_progress,
        smoke_free_days=smoke_free_days,
        smoke_free_hours=smoke_free_hours,
        money_saved=money_saved,
        next_10_days_savings=next_10_days_savings,
        craving_note=note[:500]
    )

    return {
        "headline": support.get("headline", "You can get through this craving."),
        "message": support.get("message", "Pause for 10 minutes and let the craving pass."),
        "immediate_actions": support.get("immediate_actions", []),
        "motivation": support.get("motivation", "Protect the progress you have already made."),
        "safety_note": support.get("safety_note", "Reach out to a healthcare professional if you need extra support."),
        "friend_note": support.get("friend_note", "You have got this. Stay with the next smoke-free minute."),
        "challenge": support.get("challenge", "Complete a 10-minute walk without smoking."),
        "money_ideas": support.get("money_ideas", []),
        "smoke_free_days": smoke_free_days,
        "smoke_free_hours": smoke_free_hours,
        "money_saved": money_saved,
        "next_10_days_savings": next_10_days_savings,
        "weekly_progress_days": len(weekly_progress)
    }

@router.get("/meal-recommendation")
async def meal_recommendation(uid: str, fridge_items: str = "", date: str = None):
    user_data = get_user(uid)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    if "suman" not in user_data.get("email", "").lower():
        raise HTTPException(status_code=403, detail="Meal recommendation is not enabled for this account")

    selected_date = date or datetime.today().strftime('%Y-%m-%d')
    log_data = get_daily_log(uid, selected_date) or {}
    logs = log_data.get("logs", [])
    daily_log = {
        "total_consumed": log_data.get("total_consumed", 0),
        "total_protein": log_data.get("total_protein", sum(item.get("protein", 0) for item in logs)),
        "total_fiber": log_data.get("total_fiber", sum(item.get("fiber", 0) for item in logs)),
        "total_carbs": log_data.get("total_carbs", sum(item.get("carbs", 0) for item in logs)),
        "logs": logs
    }
    target_calories = user_data.get("target_calories", 0) or 0
    remaining_calories = max(0, target_calories - daily_log["total_consumed"])
    equipment = "pan, air fryer, 5L pressure cooker, boiler, grinder"

    try:
        recommendation = recommend_next_meal(
            user_data=user_data,
            daily_log=daily_log,
            remaining_calories=remaining_calories,
            fridge_items=fridge_items[:1000],
            equipment=equipment
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Meal recommendation failed: {str(exc)}")

    return {
        "recommendation": recommendation,
        "remaining_calories": remaining_calories,
        "selected_date": selected_date,
        "equipment": equipment
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
        "coach_recommendation": report.get("coach_recommendation", "Try logging your weight and activity before analyzing."),
        "diet_analysis": report.get("diet_analysis", "No diet analysis available.")
    }
