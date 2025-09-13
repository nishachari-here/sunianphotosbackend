from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from app.utils.firebase_auth import verify_firebase_token, CurrentUser, db
from app.schemas import CommentCreate

router = APIRouter()

@router.post("/{public_id}")
def add_comment(public_id: str, payload: CommentCreate, user: CurrentUser = Depends(verify_firebase_token)):
    # ensure image exists
    img = db.collection("images").document(public_id).get()
    if not img.exists:
        raise HTTPException(status_code=404, detail="Image not found")
    col = db.collection("images").document(public_id).collection("comments")
    doc_ref = col.document()
    data = {
        "id": doc_ref.id,
        "image_id": public_id,
        "author_uid": user.uid,
        "content": payload.content,
        "created_at": datetime.utcnow()
    }
    doc_ref.set(data)
    return data

@router.get("/{public_id}")
def list_comments(public_id: str):
    img = db.collection("images").document(public_id).get()
    if not img.exists:
        raise HTTPException(status_code=404, detail="Image not found")
    col = db.collection("images").document(public_id).collection("comments")
    snapshot = col.order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    out = [d.to_dict() for d in snapshot]
    return {"comments": out}

@router.delete("/{public_id}/{comment_id}")
def delete_comment(public_id: str, comment_id: str, user: CurrentUser = Depends(verify_firebase_token)):
    comment_ref = db.collection("images").document(public_id).collection("comments").document(comment_id)
    doc = comment_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Comment not found")
    rec = doc.to_dict()
    # allow deletion by admin, editor, or comment author
    if user.uid != rec.get("author_uid") and user.role not in ("editor", "admin"):
        raise HTTPException(status_code=403, detail="Permission denied")
    comment_ref.delete()
    return {"ok": True}
