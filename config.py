import os
from pathlib import Path
from dotenv import load_dotenv
import zoneinfo

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.getenv("SECRET_KEY", "recruitment-bot-super-secure-key-2026")
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "recruitment_bot.db"))
    
    # Timezone
    TIMEZONE_STR = os.getenv("LOCAL_TIMEZONE", "Asia/Kolkata")
    try:
        TIMEZONE = zoneinfo.ZoneInfo(TIMEZONE_STR)
    except Exception:
        TIMEZONE = zoneinfo.ZoneInfo("UTC")
        TIMEZONE_STR = "UTC"

    # AI Configuration
    AI_PROVIDER = os.getenv("AI_PROVIDER", "demo").lower()  # 'demo', 'gemini', 'openai', 'custom'
    AI_API_KEY = os.getenv("AI_API_KEY", "")
    AI_MODEL = os.getenv("AI_MODEL", "gemini-1.5-flash")
    AI_ENDPOINT = os.getenv("AI_ENDPOINT", "https://generativelanguage.googleapis.com/v1beta/models")

    # Email / Notification Configuration
    EMAIL_MODE = os.getenv("EMAIL_MODE", "demo").lower()  # 'demo', 'smtp', 'gmail_api'
    EMAIL_FROM = os.getenv("EMAIL_FROM", "recruitment-bot@agency.example.com")
    EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "AI Recruitment & Internship Task Bot")
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

    # Google Sheets Configuration
    GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
    GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "AI Recruitment & Internship Task Review Bot")

    # Background Scheduler
    ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "true").lower() in ("true", "1", "yes")
    SCHEDULER_CHECK_INTERVAL_MINUTES = int(os.getenv("SCHEDULER_CHECK_INTERVAL_MINUTES", 15))
