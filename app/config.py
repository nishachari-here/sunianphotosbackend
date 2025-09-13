from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "Sunian Photos API"
    DEBUG: bool = True

    # Firebase (map env var name → field name)
    FIREBASE_CREDENTIALS: Optional[str] = Field(
        default=None, alias="GOOGLE_APPLICATION_CREDENTIALS"
    )

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    # CORS
    CORS_ORIGINS: str = "http://localhost:8000,http://localhost:8000/photos,http://localhost:5173,https://sunianphotosfrontend.vercel.app/"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True   # ✅ allow alias mapping

settings = Settings()
