from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Base de datos
    DATABASE_URL: str 
    
    # Proveedor externo
    PROVIDER_URL: str 
    PROVIDER_TIMEOUT: int = 5  # seconds If provider does not respond, cut conection and response of timeout 
    PROVIDER_RETRIES: int = 3  # Times the app retries if something goes wrong with 
    API_KEY: str
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
