from fastapi import APIRouter
from app.utils.firebase_auth import db
from app.schemas import SearchQuery

router = APIRouter()

@router.post("/")
def search(payload: SearchQuery):
    images_ref = db.collection("images")
    snapshot = images_ref.limit(500).stream()
    results = []

    for doc in snapshot:
        rec = doc.to_dict()

        # keyword search
        if payload.q:
            qlower = payload.q.lower()
            matched = False
            for f in ["title", "caption", "filename"]:
                v = (rec.get(f) or "").lower()
                if qlower in v:
                    matched = True; break
            if not matched:
                tags = rec.get("tags", [])
                if not any(qlower in str(t).lower() for t in tags):
                    continue

        # album filter
        if payload.album_id and rec.get("album_id") != payload.album_id:
            continue

        # license filter
        if payload.license and rec.get("license") != payload.license:
            continue

        # date range filter
        if payload.from_date or payload.to_date:
            uploaded_at = rec.get("uploaded_at")
            if isinstance(uploaded_at, str):  # Firestore may store as string
                uploaded_at = datetime.datetime.fromisoformat(uploaded_at)
            if payload.from_date and uploaded_at.date() < payload.from_date:
                continue
            if payload.to_date and uploaded_at.date() > payload.to_date:
                continue

        # camera metadata filter
        if payload.camera:
            exif = rec.get("exif", {})
            camera_model = (exif.get("Model") or "").lower()
            if payload.camera.lower() not in camera_model:
                continue

        results.append(rec)
        if len(results) >= (payload.limit or 50):
            break

    return {"count": len(results), "images": results}
