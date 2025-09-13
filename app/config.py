from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import json
import os
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "Sunian Photos API"
    DEBUG: bool = True

    # Firebase (map env var name → field name)
    

# Get the JSON string from the environment variable
firebase_credentials_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

# Check if the environment variable exists
if firebase_credentials_json:
    try:
        # Load the JSON string into a Python dictionary
        credentials_data = json.loads(firebase_credentials_json)

        # Now you can use this dictionary to initialize your Firebase app
        # For example, using the Firebase Admin SDK:
        # from firebase_admin import credentials, initialize_app
        # cred = credentials.Certificate(credentials_data)
        # initialize_app(cred)

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from GOOGLE_APPLICATION_CREDENTIALS: {e}")
    else:
        print("GOOGLE_APPLICATION_CREDENTIALS environment variable not found.")

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
