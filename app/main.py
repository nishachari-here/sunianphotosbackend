import os
import uuid
import datetime
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Path, Body, Depends, status
from fastapi.middleware.cors import CORSMiddleware
import cloudinary
from cloudinary.uploader import upload as cloudinary_upload
from app.config import settings
from app.schemas import ImageCreateResp
import firebase_admin
from firebase_admin import credentials, firestore, auth
from pydantic import BaseModel
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Response # Add this import at the top
# -------------------------
# Configure Cloudinary
# -------------------------
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

# -------------------------
# Firebase setup
# -------------------------
if not firebase_admin._apps:
    cred = credentials.Certificate(settings.credentials_data)
    firebase_admin.initialize_app(cred)
db = firestore.client()

# -------------------------
# Initialize FastAPI
# -------------------------
app = FastAPI(title=settings.APP_NAME)

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer()

async def get_current_user_role(token: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    try:
        print("Received Authorization Header:", token.credentials)
        decoded_token = auth.verify_id_token(token.credentials)
        uid = decoded_token['uid']
        
        print("Decoded UID:", uid)
        
        user_doc_ref = db.collection('users').document(uid)
        user_doc = user_doc_ref.get()
        if not user_doc.exists:
            print("User document not found, returning 'visitor'")
            return "visitor"
        
        user_data = user_doc.to_dict()
        user_role = user_data.get('role', 'visitor')
        print("User Role from Firestore:", user_role)
        return user_role

    except Exception as e:
        print("Authentication Failed:", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
# -------------------------
# Health Check
# -------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# -------------------------
# Upload Image
# -------------------------
@app.post("/api/upload", response_model=ImageCreateResp)
async def upload_image(
    file: UploadFile = File(...),
    album: str = Form(None),
    user_role: str = Depends(get_current_user_role)
):
    if user_role not in ["admin", "editor"]:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to upload images."
        )
    try:
        # Upload to Cloudinary
        result = cloudinary_upload(
            file.file,
            folder=album or "default",
            resource_type="image",
            overwrite=True,
        )

        if not result:
            raise HTTPException(status_code=500, detail="Upload failed")

        # Prepare image data
        image_id = str(uuid.uuid4())
        image_data = {
            "id": image_id,
            "filename": file.filename,
            "url": result.get("secure_url"),
            "mime_type": result.get("resource_type"),
            "width": result.get("width"),
            "height": result.get("height"),
            "size_bytes": result.get("bytes"),
            "title": None,
            "caption": None,
            "alt_text": None,
            "uploaded_at": datetime.datetime.utcnow().isoformat(),
            "order": int(datetime.datetime.utcnow().timestamp()),  # default order by time
        }

        # Save to Firestore
        db.collection("images").document(image_id).set(image_data)

        return ImageCreateResp(
            id=image_data["id"],
            filename=image_data["filename"],
            storage_path=image_data["url"],
            mime_type=image_data["mime_type"],
            width=image_data["width"],
            height=image_data["height"],
            size_bytes=image_data["size_bytes"],
            title=image_data["title"],
            caption=image_data["caption"],
            alt_text=image_data["alt_text"],
            uploaded_at=datetime.datetime.fromisoformat(image_data["uploaded_at"]),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# -------------------------
# Get All Images (ordered)
# -------------------------
@app.get("/api/images")
def list_images():
    try:
        docs = db.collection("images").order_by("order").stream()
        images = [doc.to_dict() for doc in docs]
        return {"images": images}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch images: {str(e)}")


# -------------------------
# Delete Image
# -------------------------


@app.delete("/api/images/{image_id}", status_code=204)
def delete_image(image_id: str = Path(..., description="ID of the image to delete"),user_role: str = Depends(get_current_user_role)):
    if user_role not in ["admin", "editor"]:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete images."
        )
    try:
        doc_ref = db.collection("images").document(image_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Image not found")

        doc_ref.delete()
        
        # Return a 204 status code with no content
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete image: {str(e)}")
# -------------------------
# Reorder Images
# -------------------------
@app.put("/api/images/reorder")
def reorder_images(
    order: List[str] = Body(..., description="List of image IDs in new order"),
    user_role: str = Depends(get_current_user_role)
):
    if user_role not in ["admin", "editor"]:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to reorder images."
        )
    try:
        batch = db.batch()
        for index, image_id in enumerate(order):
            doc_ref = db.collection("images").document(image_id)
            batch.update(doc_ref, {"order": index})
        batch.commit()
        return {"status": "ok", "order": order}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reorder images: {str(e)}")


# -------------------------
# Legacy Compatibility Route
# -------------------------
@app.post("/api/images/photos", response_model=ImageCreateResp)
async def upload_image_compat(
    file: UploadFile = File(...),
    album: str = Form(None)
):
    return await upload_image(file=file, album=album)



# ------------------------- Pydantic models (update Comment model) -------------------------
from pydantic import BaseModel, Field
from typing import Optional
import datetime as _dt

class CommentCreate(BaseModel):
    # allow both user_email and legacy user_id (optional)
    user_email: Optional[str] = None
    user_id: Optional[str] = None
    content: str

class CommentOut(BaseModel):
    user_email: Optional[str] = None
    user_id: Optional[str] = None
    content: str
    created_at: str

# Simple response model for like toggle
class LikeToggleResp(BaseModel):
    liked: bool
    total_likes: int

# ------------------------- Like toggle endpoint -------------------------
@app.post("/api/images/{image_id}/like", response_model=LikeToggleResp)
def toggle_like(image_id: str, payload: dict = Body(...)):
    """
    Toggle a like for an image. Accepts JSON body: { "user_email": "x@y.com" } (preferred)
    or { "user_id": "someId" } (legacy).
    Uses Firestore ArrayUnion/ArrayRemove to safely update arrays atomically.
    """
    # extract identifier (prefer email)
    user_email = payload.get("user_email")
    user_id = payload.get("user_id")
    identifier = user_email or user_id

    if not identifier:
        raise HTTPException(status_code=400, detail="Missing user_email or user_id in body")

    try:
        doc_ref = db.collection("images").document(image_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Image not found")

        # Ensure likes field exists and is a list
        data = doc.to_dict()
        likes = data.get("likes", [])
        if not isinstance(likes, list):
            likes = []

        # If user already in likes -> remove, else add
        if identifier in likes:
            doc_ref.update({"likes": firestore.ArrayRemove([identifier])})
            liked = False
        else:
            doc_ref.update({"likes": firestore.ArrayUnion([identifier])})
            liked = True

        # fetch final state to return accurate total (atomic ops already applied)
        final_doc = doc_ref.get()
        final_likes = final_doc.to_dict().get("likes", []) or []
        return {"liked": liked, "total_likes": len(final_likes)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle like: {str(e)}")

# ------------------------- Add comment endpoint -------------------------
@app.post("/api/images/{image_id}/comments", response_model=CommentOut)
def add_comment(image_id: str, comment: CommentCreate):
    """
    Add a comment: stores user_email (preferred) or user_id and content, with created_at timestamp.
    """
    identifier_email = comment.user_email
    identifier_id = comment.user_id
    if not identifier_email and not identifier_id:
        # You may allow anonymous comments, but if not, return error. For now we accept missing and store 'guest'.
        # If you want to require logged-in, change this to raise 401/400.
        pass

    try:
        comment_data = {
            "user_email": identifier_email,
            "user_id": identifier_id,
            "content": comment.content,
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
        # store in subcollection "comments"
        db.collection("images").document(image_id).collection("comments").add(comment_data)
        return comment_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add comment: {str(e)}")

# ------------------------- List comments -------------------------
@app.get("/api/images/{image_id}/comments", response_model=List[CommentOut])
def list_comments(image_id: str):
    try:
        docs = (
            db.collection("images")
            .document(image_id)
            .collection("comments")
            .order_by("created_at")
            .stream()
        )
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch comments: {str(e)}")
