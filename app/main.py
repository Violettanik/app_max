from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .database import engine, get_db
from .models import Base, User, AuthImage
from prometheus_client import make_asgi_app, Counter, Histogram, Gauge
import time
import logging
from .generate_image import generate_user_image
import os

Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="/app/static"), name="static")

def create_initial_users():
    db: Session = next(get_db())
    
    users = [
        ["user1", "user1@yandex.ru", "password1"],
        ["user2", "user2@yandex.ru", "password2"], 
        ["user3", "user3@yandex.ru", "password3"]
    ]
    
    for username, email, password in users:
        user = User(username=username, email=email, password=password)
        db.add(user)
        db.flush()  # Чтобы получить ID пользователя
        
        filename = f"{username}_auth.jpg"
        filepath = os.path.join(os.getenv("AUTH_IMAGES_DIR"), filename)
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        generate_user_image(filepath)
        
        auth_image = AuthImage(
            filename=filename,
            filepath=filepath,
            owner_username=username
        )
        db.add(auth_image)
    
    db.commit()
    db.close()

@app.on_event("startup")
async def on_startup():
    create_initial_users()

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP Requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP Request Latency',
    ['method', 'endpoint']
)

UPLOADED_IMAGES = Counter(
    'uploaded_images_total',
    'Total Uploaded Images'
)

AUTH_ERRORS = Counter(
    'auth_errors_total',
    'Total Authentication Errors'
)

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    method = request.method
    endpoint = request.url.path
    
    try:
        response = await call_next(request)
    except Exception as e:
        if "auth" in endpoint or "login" in endpoint or "register" in endpoint:
            AUTH_ERRORS.inc()
        REQUEST_COUNT.labels(method, endpoint, 500).inc()
        raise e
    
    latency = time.time() - start_time
    REQUEST_LATENCY.labels(method, endpoint).observe(latency)
    REQUEST_COUNT.labels(method, endpoint, response.status_code).inc()
    
    return response

from .routers import auth,images
app.include_router(auth.router)
app.include_router(images.router)

@app.get("/")
async def home():
    return {"message": "Welcome to Simple Auth with PostgreSQL"}
