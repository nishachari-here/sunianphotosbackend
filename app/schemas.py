from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
import datetime

# --------------------
# Users
# --------------------
class UserCreate(BaseModel):
    username: str = Field(..., description="Unique username for the user")
    email: str = Field(..., description="User's email address")
    password: str = Field(..., description="Plaintext password (will be hashed)")


class UserOut(BaseModel):
    id: UUID = Field(..., description="Unique user ID")
    username: str = Field(..., description="User's display name")
    email: str = Field(..., description="User's email address")
    role: str = Field(..., description="Role assigned to the user (e.g. visitor, editor, admin)")

    model_config = {"from_attributes": True}


# --------------------
# Images
# --------------------
class ImageCreateResp(BaseModel):
    id: UUID = Field(..., description="Unique image ID")
    filename: str = Field(..., description="Original filename of the uploaded image")
    storage_path: str = Field(..., description="Cloud storage path of the image")
    mime_type: Optional[str] = Field(None, description="MIME type of the image (e.g., image/jpeg)")
    width: Optional[int] = Field(None, description="Width of the image in pixels")
    height: Optional[int] = Field(None, description="Height of the image in pixels")
    size_bytes: Optional[int] = Field(None, description="Size of the image in bytes")
    title: Optional[str] = Field(None, description="Title of the image")
    caption: Optional[str] = Field(None, description="Caption describing the image")
    alt_text: Optional[str] = Field(None, description="Alt text for accessibility")
    uploaded_at: datetime.datetime = Field(..., description="Timestamp when the image was uploaded")

    model_config = {"from_attributes": True}


class ImageEdit(BaseModel):
    title: Optional[str] = Field(None, description="Updated title of the image")
    caption: Optional[str] = Field(None, description="Updated caption of the image")
    alt_text: Optional[str] = Field(None, description="Updated alt text for accessibility")
    license: Optional[str] = Field(None, description="Updated license type (e.g., CC-BY)")
    privacy: Optional[str] = Field(None, description="Privacy setting (e.g., public, private)")
    album_id: Optional[str] = Field(None, description="Album ID to associate this image with")
    tags: Optional[List[str]] = Field(None, description="List of tags associated with the image")


# --------------------
# Albums
# --------------------
class AlbumCreate(BaseModel):
    title: str = Field(..., description="Title of the album")
    description: Optional[str] = Field("", description="Description of the album")


# --------------------
# Comments
# --------------------
class CommentCreate(BaseModel):
    content: str = Field(..., description="Content of the comment")


# --------------------
# Search
# --------------------
class SearchQuery(BaseModel):
    q: Optional[str] = Field(
        None, description="Keyword to search in title, caption, filename, or tags"
    )
    album_id: Optional[str] = Field(
        None, description="Filter by album ID"
    )
    from_date: Optional[datetime.date] = Field(
        None, description="Filter images uploaded on or after this date (YYYY-MM-DD)"
    )
    to_date: Optional[datetime.date] = Field(
        None, description="Filter images uploaded on or before this date (YYYY-MM-DD)"
    )
    camera: Optional[str] = Field(
        None, description="Filter by camera model (from EXIF metadata)"
    )
    license: Optional[str] = Field(
        None, description="Filter by license type (e.g., CC-BY, All Rights Reserved)"
    )
    limit: Optional[int] = Field(
        50, ge=1, le=100, description="Maximum number of results to return (default 50, max 100)"
    )
