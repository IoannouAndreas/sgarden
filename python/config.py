"""Application configuration loaded from environment variables."""
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


class Settings(BaseSettings):
    """Runtime settings sourced from the environment / .env file."""
    database_url: str = "mongodb://localhost:27017/sgarden"
    port: int = 4000
    server_secret: str = "sgarden-secret-key"
    jwt_expiration_hours: int = 24

    class Config:
        """Pydantic settings configuration."""
        env_file = "../.env"
        extra = "ignore"


settings = Settings()
