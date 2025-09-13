# app/utils/firebase_auth.py
from fastapi import Depends, HTTPException, status
from pydantic import BaseModel
import firebase_admin
from firebase_admin import auth, firestore
from typing import Optional, Dict

# This should be your Firebase project's service account key file
# Make sure to initialize this once in your main application file.
# cred = firebase_admin.credentials.Certificate("path/to/your/service-account-key.json")
# firebase_admin.initialize_app(cred)
db = firestore.client()

# Pydantic model for the current user, based on the decoded token
class CurrentUser(BaseModel):
    uid: str
    email: str
    role: Optional[str] = "user"

# Dependency to verify the Firebase ID token from the Authorization header
async def verify_firebase_token(id_token: str = Depends(oauth2_scheme)):
    try:
        # Verify the token using Firebase Admin SDK
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        
        # Get user's role from Firestore
        user_ref = db.collection('users').document(uid)
        user_doc = user_ref.get()
        
        user_role = 'user'
        if user_doc.exists:
            user_role = user_doc.to_dict().get('role', 'user')
            
        return CurrentUser(uid=uid, email=decoded_token['email'], role=user_role)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )