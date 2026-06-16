import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    FIREBASE_WEB_API_KEY: str = ""
    
    @property
    def FIREBASE_CREDENTIALS_PATH(self) -> str:
        # Check multiple possible locations for Render secret files
        possible_paths = [
            "/etc/secrets/config/serviceAccountKey.json",  # Render's secret directory
            "/etc/secrets/serviceAccountKey.json",         # Alternate Render path
            "config/serviceAccountKey.json",               # Local development
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # If none exist, return the first path (will error with clear message)
        return possible_paths[0]

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        env_file_encoding = 'utf-8'

settings = Settings()