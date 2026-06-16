from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routes import auth, onboard

app = FastAPI(title="AI Fitness Agent Blueprint")

# Mount Static and Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Include Modular Routes
app.include_router(auth.router)
app.include_router(onboard.router)

@app.get("/")
async def root(request: Request):
    # Redirect to login page initially
    return templates.TemplateResponse(name="login.html", request=request, context={})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main.py", host="127.0.0.1", port=8000, reload=True)