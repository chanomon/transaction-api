from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Base de datos
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@postgres:5432/transaction_db"
    
    # Proveedor externo
    PROVIDER_URL: str = "http://wiremock:8080"
    PROVIDER_TIMEOUT: int = 5  # seconds If provider does not respond, cut conection and response of timeout 
    PROVIDER_RETRIES: int = 3  # Times the app retries if something goes wrong with 
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
