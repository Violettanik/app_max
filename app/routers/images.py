from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
import os
from dotenv import load_dotenv
load_dotenv()
from pathlib import Path
from sqlalchemy.orm import Session
from ..models import Image, User
from ..database import get_db
import shutil
from ..main import UPLOADED_IMAGES

router = APIRouter()

IMAGES_DIR = os.getenv("IMAGES_DIR")
os.makedirs(IMAGES_DIR, exist_ok=True)

@router.post("/upload")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    username = request.cookies.get("username")
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
    username = request.cookies.get("username")
    if not username:
        return RedirectResponse(url="/login")

    db_image = db.query(Image).filter(Image.id == image_id).first()
    if not db_image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(db_image.filepath)

@router.get("/user/images")
async def get_user_images(
    request: Request,
    db: Session = Depends(get_db)
):
    username = request.cookies.get("username")
    if not username:
        return RedirectResponse(url="/login")

    images = db.query(Image).filter(Image.owner_username == username).all()
    return images
