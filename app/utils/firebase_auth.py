from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import firebase_admin
from firebase_admin import credentials, auth, firestore
from app.config import settings
from typing import Optional

# Initialize Firebase Admin once
if not firebase_admin._apps:
    if not settings.FIREBASE_CREDENTIALS:
        raise RuntimeError("Missing GOOGLE_APPLICATION_CREDENTIALS in .env")
    
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS)
    firebase_admin.initialize_app(cred)

db = firestore.client()
security = HTTPBearer()

class CurrentUser:
    def __init__(self, uid: str, email: Optional[str], role: str):
        self.uid = uid
        self.email = email
        self.role = role

def verify_firebase_token(creds: HTTPAuthorizationCredentials = Security(security)) -> CurrentUser:
    token = creds.credentials
    try:
        decoded = auth.verify_id_token(token)
        uid = decoded.get("uid")
        email = decoded.get("email")
        # read role from Firestore: collection 'users', doc = uid
        doc_ref = db.collection("users").document(uid)
        doc = doc_ref.get()
        role = "visitor"
        if doc.exists:
            data = doc.to_dict()
            role = data.get("role", "visitor")
        # Return a simple user object
        return CurrentUser(uid=uid, email=email, role=role)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
