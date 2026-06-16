import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    FIREBASE_WEB_API_KEY: str = ""
    
    @property
    def FIREBASE_CREDENTIALS_PATH(self) -> str:
        # Check Render's secret files location first
        render_secret_path = "/etc/secrets/config/serviceAccountKey.json"
        if os.path.exists(render_secret_path):
            return render_secret_path
        # Fall back to local path for development
        return "config/serviceAccountKey.json"

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        env_file_encoding = 'utf-8'

settings = Settings()