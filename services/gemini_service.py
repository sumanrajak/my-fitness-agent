from pydantic import BaseModel
from google import genai
from google.genai import types
from config import settings

# Initialize the new GenAI Client
# It automatically looks for the GEMINI_API_KEY environment variable
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Define the expected structured output schema using Pydantic
class CalorieAnalysis(BaseModel):
    maintenance_calories: int
    target_calories: int
    insights_summary: str

def analyze_user_fitness(profile_data: dict) -> dict:
    """
    Sends user details to Gemini using the new google-genai SDK 
    and returns a validated dictionary matching the CalorieAnalysis schema.
    """
    
    prompt = f"""
    You are an expert fitness coach and AI agent. Analyze the following user profile:
    - Age: {profile_data.get('age')}
    - Biological Sex: {profile_data.get('sex')}
    - Height: {profile_data.get('height')} cm
    - Current Weight: {profile_data.get('weight')} kg
    - Activity Level: {profile_data.get('activity_level')}
    - Personal Context & Insights: {profile_data.get('context')}
    - Target Timeline: {profile_data.get('timeline')}
    
    Calculate their exact daily maintenance calories and target calories to safely reach their goal within their timeline. 
    Provide a concise summary of insights.
    """
    
    # Using the recommended 'gemini-2.5-flash' model for text tasks
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CalorieAnalysis,
            temperature=0.2, # Lower temperature for more stable calculations
        ),
    )
    
    # The SDK parses it directly into the schema if requested, 
    # but since it returns valid JSON matching our Pydantic object, we can safely parse it
    import json
    return json.loads(response.text)

class FoodEstimation(BaseModel):
    itemized_breakdown: str  # e.g., "Eggs (140 kcal), Toast (150 kcal)"
    estimated_calories: int  # e.g., 290

def estimate_food_calories(food_text: str) -> dict:
    """
    Uses Gemini 2.5 to analyze a natural language food description
    and return an estimated calorie count with an itemized breakdown.
    """
    prompt = f"""
    You are an expert AI nutritionist and calorie estimator. 
    Analyze the following meal description: '{food_text}'
    
    Estimate the total calories as accurately as possible based on standard nutritional data.
    Provide a brief, clean itemized breakdown text of the components and their individual calories.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FoodEstimation,
            temperature=0.1,  # Low temperature for objective calorie calculations
        ),
    )
    
    import json
    return json.loads(response.text)