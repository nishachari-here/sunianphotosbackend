from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Query
from typing import List, Optional
import cloudinary
import cloudinary.uploader
import cloudinary.api
from app.config import settings
from app.utils.firebase_auth import verify_firebase_token, CurrentUser, db
from app.schemas import ImageEdit   # ✅ add this
from google.cloud import firestore  # ✅ fix for query ordering
from datetime import datetime, timezone
from PIL import Image, ExifTags
from io import BytesIO

router = APIRouter()

# Init Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

def extract_exif_bytes(b: bytes):
    try:
        img = Image.open(BytesIO(b))
        raw = getattr(img, "_getexif", lambda: {})() or {}
        exif = {}
        for k, v in raw.items():
            name = ExifTags.TAGS.get(k, k)
            exif[name] = v
        return exif
    except Exception:
        return {}

@router.post("/photos")
async def upload_image(
    file: UploadFile = File(...), 
    title: Optional[str] = None, 
    album_id: Optional[str] = None, 
    privacy: str = "public", 
    user: CurrentUser = Depends(verify_firebase_token)
):
    """
    Uploads the image to Cloudinary and stores metadata in Firestore.
    """
    # Initialize public_id outside the try block to ensure it's always defined
    public_id = None
    
    try:
        contents = await file.read()
        
        # extract exif locally (optional)
        exif = extract_exif_bytes(contents)
        
        # upload to cloudinary under folder per user
        folder = f"sunian-photos/{user.uid}"
        
        result = cloudinary.uploader.upload(
            BytesIO(contents),
            folder=folder,
            resource_type="image",
            use_filename=True,
            unique_filename=True
        )
        
        public_id = result.get("public_id")
        url = result.get("secure_url")
        width = result.get("width")
        height = result.get("height")
        format_ = result.get("format")
        bytes_len = result.get("bytes")
        
        # store metadata in Firestore collection 'images', doc id = public_id
        data = {
            "public_id": public_id,
            "url": url,
            "filename": file.filename,
            "mime_type": file.content_type,
            "width": width,
            "height": height,
            "size_bytes": bytes_len,
            "title": title or "",
            "caption": "",
            "alt_text": "",
            "license": "",
            "privacy": privacy,
            "uploaded_by": user.uid,
            "uploaded_at": datetime.utcnow(),
            "exif": exif,
            "album_id": album_id or None,
            "tags": [],
        }
        
        db.collection("images").document(public_id).set(data)
        return {"ok": True, "public_id": public_id, "url": url}

    except Exception as e:
        # Now, `public_id` is defined and can be returned in the error message
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred during upload. Public ID: {public_id}. Error: {e}"
        )

@router.get("/")
def list_images(q: Optional[str] = Query(None), album_id: Optional[str] = Query(None), limit: int = 50, skip: int = 0, uid: Optional[str] = None):
    """
    List images with optional search q and album filter.
    """
    print("Fetching images from Firestore...")
    images_ref = db.collection("images")
    snapshot = images_ref.stream()

    results = []
    for doc in snapshot:
        rec = doc.to_dict()
        results.append(rec)
    
    print(f"Fetched {len(results)} documents before filtering.")
    
    final_results = []
    for rec in results:
        # privacy filter
        if rec.get("privacy", "public") != "public":
            if uid is None or rec.get("uploaded_by") != uid:
                print(f"Skipping private/unlisted image: {rec.get('public_id')}")
                continue
        if album_id and rec.get("album_id") != album_id:
            print(f"Skipping image from wrong album: {rec.get('public_id')}")
            continue
        if q:
            # ... your search logic ...
            qlower = q.lower()
            matched = False
            for f in ["title", "caption", "filename"]:
                v = rec.get(f) or ""
                if qlower in v.lower():
                    matched = True; break
            if not matched:
                tags = rec.get("tags", [])
                if any(qlower in str(t).lower() for t in tags):
                    matched = True
            if not matched:
                print(f"Skipping non-matching image: {rec.get('public_id')}")
                continue
        
        final_results.append(rec)

    # apply skip/limit
    final_results = final_results[skip: skip + limit]
    
    print(f"Returning {len(final_results)} images after filtering.")
    
    return {"count": len(final_results), "images": final_results}


@router.get("/{public_id}")
def get_image(public_id: str, user: CurrentUser = Depends(verify_firebase_token)):
    doc = db.collection("images").document(public_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Not found")
    rec = doc.to_dict()
    # privacy check: if private and not owner and not admin/editor -> deny
    privacy = rec.get("privacy", "public")
    if privacy == "private" and user.role not in ("admin", "editor") and user.uid != rec.get("uploaded_by"):
        raise HTTPException(status_code=403, detail="Access denied")
    return rec

@router.post("/{public_id}/edit")
def edit_image(public_id: str, payload: ImageEdit, user: CurrentUser = Depends(verify_firebase_token)):
    doc_ref = db.collection("images").document(public_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Not found")
    rec = doc.to_dict()
    if user.uid != rec.get("uploaded_by") and user.role not in ("editor", "admin"):
        raise HTTPException(status_code=403, detail="Permission denied")

    updates = payload.model_dump(exclude_unset=True)  # ✅ v2-safe
    allowed = {"title", "caption", "alt_text", "license", "privacy", "album_id", "tags"}
    to_update = {k: v for k, v in updates.items() if k in allowed}

    if to_update:
        doc_ref.set(to_update, merge=True)
    return {"ok": True, "updated": to_update}

@router.delete("/{public_id}")
def delete_image(public_id: str, user: CurrentUser = Depends(verify_firebase_token)):
    doc_ref = db.collection("images").document(public_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Not found")
    rec = doc.to_dict()
    # permission: uploader or editor/admin
    if user.uid != rec.get("uploaded_by") and user.role not in ("editor", "admin"):
        raise HTTPException(status_code=403, detail="Permission denied")
    # delete from Cloudinary and Firestore
    try:
        cloudinary.uploader.destroy(public_id, invalidate=True, resource_type="image")
    except Exception as e:
        # log but continue to remove metadata
        pass
    doc_ref.delete()
    return {"ok": True, "deleted": public_id}
