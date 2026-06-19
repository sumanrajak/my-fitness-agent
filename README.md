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

## Project Structure
- `main.py`: Application entry point, router inclusion, and static/template mounting.
- `routes/auth.py`: User registration and login logic via Firebase REST API.
- `routes/onboard.py`: Core logic for onboarding, dashboard rendering, daily logging, AI reviews, and reporting.
- `services/gemini_service.py`: Encapsulates Gemini AI calls, deterministic calorie math, and fallback logic.
- `services/firebase_service.py`: Handles Firebase/Firestore initialization and user data queries.
- `config/settings.py`: Environment variable and configuration management.
- `templates/`: Jinja2 HTML templates for the frontend UI.
- `static/`: Static assets (CSS, JS, images).
