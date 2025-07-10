from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .database import engine
from .models import Base
from prometheus_client import make_asgi_app, Counter, Histogram, Gauge
import time
import logging

Base.metadata.create_all(bind=engine)

logging.basicConfig(
    filename='/var/log/app/app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

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

UPLOADED_IMAGES = Gauge(
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
