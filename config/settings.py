import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    FIREBASE_CREDENTIALS_PATH: str = "config/serviceAccountKey.json"
    FIREBASE_WEB_API_KEY: str

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        env_file_encoding = 'utf-8'

settings = Settings()