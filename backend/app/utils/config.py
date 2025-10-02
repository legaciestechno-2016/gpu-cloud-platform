from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/gpucloud"
    REDIS_URL: str = "redis://localhost:6379"
    
    # Azure
    AZURE_SUBSCRIPTION_ID: str = ""
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    USE_MOCK_AZURE: bool = True
    
    # Auth
    JWT_SECRET: str = "change-this-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    
    # Application
    APP_ENV: str = "development"
    DEBUG: bool = True
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # GPU Pricing (per hour)
    GPU_PRICE_T4: float = 0.99
    GPU_PRICE_A10G: float = 1.99
    GPU_PRICE_A100: float = 3.99
    
    # Free credits
    NEW_USER_CREDITS: float = 50.0
    
    # AutoPause
    AUTOPAUSE_CHECK_INTERVAL: int = 30
    AUTOPAUSE_IDLE_THRESHOLD: int = 120
    AUTOPAUSE_GPU_USAGE_THRESHOLD: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()