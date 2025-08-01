import os
import platform
import logging
import pytesseract
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import Optional

logger = logging.getLogger(__name__)

load_dotenv()

class Settings(BaseSettings):
    # IMAP Settings
    IMAP_SERVER: str
    IMAP_USER: str
    IMAP_PASSWORD: str

    # SMTP Settings
    SMTP_SERVER: str
    SMTP_PORT: int
    SENDER_EMAIL: str
    SENDER_PASSWORD: str

    # Groq API Key
    GROQ_API_KEY: str

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
