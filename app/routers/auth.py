from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from ..main import AUTH_ERRORS
from ..models import User, Image, AuthImage
from ..database import get_db, redis_client
from ..generate_image import generate_user_image
import os
import uuid
import json
from datetime import timedelta

AUTH_IMAGES_DIR = os.getenv("AUTH_IMAGES_DIR")

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

def create_session(user_id: int, username: str):
    session_id = str(uuid.uuid4())
    session_data = {
        "user_id": user_id,
        "username": username
    }
    # Store session in Redis with 30 minutes expiration
    redis_client.setex(session_id, timedelta(minutes=30), json.dumps(session_data))
    return session_id

def get_session(session_id: str):
    if not session_id:
        return None
    session_data = redis_client.get(session_id)
    if not session_data:
        return None
    return json.loads(session_data)

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
async def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.username == username).first():
        AUTH_ERRORS.inc()
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Username already exists"
        })
    
    if db.query(User).filter(User.email == email).first():
        AUTH_ERRORS.inc()
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Email already exists"
        })
    
    user = User(username=username, email=email, password=password)
    db.add(user)
    db.commit()
    
    filename = f"{username}_auth.jpg"
    filepath = os.path.join(AUTH_IMAGES_DIR, filename)
    generate_user_image(filepath)
    
    auth_image = AuthImage(
        filename=filename,
        filepath=filepath,
        owner_username=username
    )
    db.add(auth_image)
    db.commit()

    return RedirectResponse(url="/login", status_code=303)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    
    if not user or user.password != password:
        AUTH_ERRORS.inc()
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid credentials"
        })
 
    session_id = create_session(user.id, user.username)
    response = RedirectResponse(url="/profile", status_code=303)
    response.set_cookie(key="session_id", value=session_id, httponly=True)
    return response

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, username: str = "", db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    session_data = get_session(session_id)

    if not session_data:
        return RedirectResponse(url="/login")

    username = session_data["username"]

    user = db.query(User).filter(User.username == username).first()
    if not user:
        return RedirectResponse(url="/login")
    images = db.query(Image).filter(Image.owner_username == username).all()

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "username": username,
        "images": images
    })

@router.post("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id:
        redis_client.delete(session_id)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("username")
    return response
