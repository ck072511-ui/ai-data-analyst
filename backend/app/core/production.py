import os
from pydantic_settings import BaseSettings

class ProductionConfig(BaseSettings):
    # App Settings
    ENV: str = os.getenv("ENVIRONMENT", "production")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "prod-secure-token-default-change-me-please")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

    # DB Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./prod_analytics.db")

    # Security caps
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
    MAX_REQUEST_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024

    # Security Headers config
    ALLOWED_HOSTS: list = os.getenv("ALLOWED_HOSTS", "*").split(",")
    SECURE_HEADERS: dict = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';",
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload"
    }

    # Backup parameters
    BACKUP_DIRECTORY: str = os.getenv("BACKUP_DIRECTORY", "./database_backups")

    class Config:
        case_sensitive = True

settings = ProductionConfig()
