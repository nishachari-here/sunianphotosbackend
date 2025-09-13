from fastapi import APIRouter, Depends, HTTPException
from app.utils.firebase_auth import verify_firebase_token, CurrentUser, db
from app.utils.firebase_auth import security
from app.schemas import UserOut

router = APIRouter()

@router.get("/me", response_model=UserOut)
def me(user: CurrentUser = Depends(verify_firebase_token)):
    return UserOut(
        id=user.uid,
        username="unknown",  # ✅ placeholder (replace if you store usernames in Firestore)
        email=user.email,
        role=user.role,
    )

@router.post("/{target_uid}/role")
def set_role(target_uid: str, role: str, user: CurrentUser = Depends(verify_firebase_token)):
    # only admin can set roles
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    if role not in ["admin", "editor", "visitor"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    doc_ref = db.collection("users").document(target_uid)
    doc_ref.set({"role": role}, merge=True)
    return {"uid": target_uid, "role": role}
