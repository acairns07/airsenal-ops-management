"""Configuration module for the application."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
if os.getenv("ENVIRONMENT", "production") != "production":
    try:
        load_dotenv(dotenv_path=ROOT_DIR / ".env", override=False)
    except Exception:
        pass


class Config:
    """Application configuration."""

    # MongoDB
    MONGO_URL = os.environ['MONGO_URL']
    DB_NAME = os.environ['DB_NAME']

    # JWT
    JWT_SECRET = os.environ.get('JWT_SECRET')
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET environment variable is required")
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_HOURS = 12

    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')

    # Database paths
    PERSISTENT_DB_PATH = os.getenv("PERSISTENT_DB_PATH", "/data/airsenal/data.db")
    LOCAL_DB_PATH = os.getenv("LOCAL_DB_PATH", "/tmp/airsenal.db")

    # Encryption key for secrets (32 bytes for Fernet)
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
    if not ENCRYPTION_KEY:
        # Generate a key if not provided (for development only)
        from cryptography.fernet import Fernet
        ENCRYPTION_KEY = Fernet.generate_key().decode()
        print(f"⚠️  WARNING: Using generated encryption key. Set ENCRYPTION_KEY env var in production!")
        print(f"Generated key: {ENCRYPTION_KEY}")

    # Rate limiting
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))

    # Job queue
    MAX_JOB_RETRIES = int(os.getenv('MAX_JOB_RETRIES', '3'))
    JOB_RETRY_DELAY_SECONDS = int(os.getenv('JOB_RETRY_DELAY_SECONDS', '60'))
    MAX_LOG_LINES = int(os.getenv('MAX_LOG_LINES', '2000'))

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.getenv('LOG_FORMAT', 'json')  # 'json' or 'text'


config = Config()
