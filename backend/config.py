import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')


class Settings:
    # MongoDB
    MONGO_URL: str = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME: str = os.environ.get('DB_NAME', 'traffic_engine_db')
    
    # JWT
    JWT_SECRET_KEY: str = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    JWT_ALGORITHM: str = os.environ.get('JWT_ALGORITHM', 'HS256')
    JWT_EXPIRATION_MINUTES: int = int(os.environ.get('JWT_EXPIRATION_MINUTES', 43200))
    
    # API Keys
    GROQ_API_KEY: str = os.environ.get('GROQ_API_KEY', '')
    EXA_API_KEY: str = os.environ.get('EXA_API_KEY', '')
    
    # Redis & Celery
    REDIS_URL: str = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL: str = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND: str = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    
    # CORS
    CORS_ORIGINS: str = os.environ.get('CORS_ORIGINS', '*')
    
    # Scraping configs
    REDDIT_KEYWORDS = [
        "email verifier", "b2b leads", "CRM", "sales outreach",
        "growth hacking", "email marketing", "startup tools"
    ]
    
    QUORA_KEYWORDS = [
        "best email checker", "verify email list", "find company from IP",
        "b2b lead generation", "email validation"
    ]
    
    COMPETITORS = [
        "apollo.io", "zoominfo", "hunter.io", "neverbounce",
        "snov.io", "clearbit"
    ]


settings = Settings()
