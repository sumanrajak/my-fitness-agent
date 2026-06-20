from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.auth_routes import router as auth_router
from api.onboarding_routes import router as onboard_router
from api.dashboard_routes import router as dashboard_router
from api.tracking_routes import router as tracking_router

app = FastAPI(title="AI Fitness Agent Blueprint")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router)
app.include_router(onboard_router)
app.include_router(dashboard_router)
app.include_router(tracking_router)

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(name="login.html", request=request, context={})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main.py", host="127.0.0.1", port=8000, reload=True)