from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from ..main import AUTH_ERRORS
from ..models import User, Image
from ..database import get_db

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

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
 
    response = RedirectResponse(url="/profile", status_code=303)
    response.set_cookie(key="username", value=username)
    return response

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, username: str = "", db: Session = Depends(get_db)):
    username = request.cookies.get("username")
    if not username:
        return RedirectResponse(url="/login")
    
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
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("username")
    return response
