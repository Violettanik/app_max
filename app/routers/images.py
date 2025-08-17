from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
import os
import json
from dotenv import load_dotenv
load_dotenv()
from pathlib import Path
from sqlalchemy.orm import Session
from ..models import Image, User, AuthImage
from ..database import get_db, redis_client
import shutil
from ..main import UPLOADED_IMAGES

router = APIRouter()

IMAGES_DIR = os.getenv("IMAGES_DIR")
os.makedirs(IMAGES_DIR, exist_ok=True)

def get_session(session_id: str):
    if not session_id:
        return None
    session_data = redis_client.get(session_id)
    if not session_data:
        return None
    return json.loads(session_data)

@router.get("/auth_images/{username}")
async def get_auth_image(request: Request, username: str, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    session_data = get_session(session_id)

    if not session_data:
        return RedirectResponse(url="/login")

    current_username = session_data["username"]
    
    if username != current_username:
        return RedirectResponse(url="/profile")

    auth_image = db.query(AuthImage).filter(AuthImage.owner_username == username).first()
    if not auth_image:
        raise HTTPException(status_code=404, detail="Auth image not found")
    
    return FileResponse(auth_image.filepath)

@router.post("/upload")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    session_id = request.cookies.get("session_id")
    session_data = get_session(session_id)
    if not session_data:
        return JSONResponse(
            content={"error": "Not authenticated"},
            status_code=401
        )
    
    username = session_data["username"]
    try:
        UPLOADED_IMAGES.inc()
        file_path = os.path.join(IMAGES_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    
        db_image = Image(
            filename=file.filename,
            filepath=file_path,
            owner_username=username
        )
        db.add(db_image)
        db.commit()
        db.refresh(db_image)

        return JSONResponse(
            content={"filename": file.filename},
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@router.get("/images/{image_id}")
async def get_image(request: Request, image_id: int, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    session_data = get_session(session_id)

    if not session_data:
        return RedirectResponse(url="/login")

    current_username = session_data["username"]
    db_image = db.query(Image).filter(Image.id == image_id).first()
    if not db_image:
        raise HTTPException(status_code=404, detail="Image not found")

    if db_image.owner_username != current_username:
        return RedirectResponse(url="/profile")

    return FileResponse(db_image.filepath)

@router.get("/user/images")
async def get_user_images(
    request: Request,
    db: Session = Depends(get_db)
):
    session_id = request.cookies.get("session_id")
    session_data = get_session(session_id)
    if not session_data:
        return RedirectResponse(url="/login")

    username = session_data["username"]
    images = db.query(Image).filter(Image.owner_username == username).all()
    return images
