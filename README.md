# AI Fitness Agent Blueprint

An AI-powered fitness tracking web application built with FastAPI, Firebase, and Gemini AI. It helps users onboard by analyzing their goals, tracks their daily fitness journey, allows natural language meal logging with AI calorie estimation, and provides AI-generated fitness insights and progress reviews.

## Features

- **User Authentication**: Secure user registration and login using Firebase Authentication.
- **AI-Powered Onboarding**: Uses Gemini AI to deterministically calculate daily target calories, maintenance calories, and required deficit based on user profile, weight, and timeline.
- **Smart Food Logging**: Log meals using natural language descriptions (e.g., "2 parathas with curd"). Gemini AI automatically estimates total calories, protein, fiber, and carbs with a detailed itemized breakdown.
- **Daily Dashboard**: Track weight, daily steps, exercise minutes, and calorie consumption against AI-calculated targets.
- **Progress & Consistency Analysis**: Receive AI-generated day-wise progress reports, consistency assessments, and actionable coaching tips.
- **Trends & Weekly Reports**: Visualize weight and calorie trends over time and generate comprehensive AI-driven weekly fitness reports based on your data.

## Tech Stack

- **Backend Framework**: Python, FastAPI
- **AI Integration**: Google GenAI (Gemini Models)
- **Database & Auth**: Google Cloud Firestore, Firebase Admin SDK
- **Templating**: Jinja2
- **Frontend**: HTML, CSS (via Static Files & Jinja2 Templates)

## Setup & Installation

### 1. Prerequisites
Ensure you have Python 3.9+ installed on your system.

### 2. Virtual Environment
Clone the repository, navigate to the project directory, and create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuration
Create a `.env` file in the root directory and add the necessary API keys:
```env
FIREBASE_WEB_API_KEY=your_firebase_web_api_key
GEMINI_API_KEY=your_gemini_api_key
```
You must also download your Firebase Service Account JSON key from the Firebase Console and place it at `config/serviceAccountKey.json`.

### 5. Run the Application
Start the FastAPI development server:
```bash
uvicorn main:app --reload
```
The application will be accessible at `http://127.0.0.1:8000`.

## 🐳 Running with Docker

Alternatively, you can run the entire application inside a Docker container.

### 1. Build the Docker Image
```bash
docker build -t fitness-agent .
```

### 2. Run the Container
Ensure your `.env` file is populated with your API keys. Then, map your environment file and the port to the container:
```bash
docker run -p 8000:8000 --env-file .env -v $(pwd)/config/serviceAccountKey.json:/app/config/serviceAccountKey.json fitness-agent
```
The app will now be available at `http://127.0.0.1:8000`.

## Project Structure
- `main.py`: Application entry point, router inclusion, and static/template mounting.
- `api/`: Modular FastAPI routers for authentication, onboarding, dashboard, and tracking.
- `services/`: Business logic decoupling DB access (`user_service.py`, `tracking_service.py`) and LLM processing (`ai_service.py`).
- `schemas/`: Pydantic models for request/response validation.
- `utils/`: Deterministic math calculations (`fitness_math.py`).
- `core/`: Environment variables and configuration logic.
- `db/`: Firestore setup and schema documentation.
- `templates/`: Jinja2 HTML templates for the frontend UI.
- `static/`: Static assets (CSS, JS, images).
