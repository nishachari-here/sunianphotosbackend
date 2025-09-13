from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from app.utils.firebase_auth import verify_firebase_token, CurrentUser, db
from app.schemas import AlbumCreate

router = APIRouter()

@router.post("/")
def create_album(payload: AlbumCreate, user: CurrentUser = Depends(verify_firebase_token)):
    doc_ref = db.collection("albums").document()
    data = {
        "id": doc_ref.id,
        "title": payload.title,
        "description": payload.description or "",
        "created_by": user.uid,
        "created_at": datetime.utcnow(),
        "image_ids": [],
    }
    doc_ref.set(data)
    return data

@router.get("/")
def list_albums():
    snapshot = db.collection("albums").stream()
    out = [doc.to_dict() for doc in snapshot]
    return {"albums": out}

@router.get("/{album_id}")
def get_album(album_id: str):
    doc = db.collection("albums").document(album_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Album not found")
    return doc.to_dict()

@router.post("/{album_id}/add")
def add_image_to_album(album_id: str, public_id: str, user: CurrentUser = Depends(verify_firebase_token)):
    # only owner/editor/admin can add
    album_ref = db.collection("albums").document(album_id)
    album = album_ref.get()
    if not album.exists:
        raise HTTPException(status_code=404, detail="Album not found")
    album_ref.update({"image_ids": firestore.ArrayUnion([public_id])})
    # also update image doc album_id
    db.collection("images").document(public_id).set({"album_id": album_id}, merge=True)
    return {"ok": True}
