from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .database import engine
from .models import Base

Base.metadata.create_all(bind=engine)

app = FastAPI()
#app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

from .routers import auth,images
app.include_router(auth.router)
app.include_router(images.router)

@app.get("/")
async def home():
    return {"message": "Welcome to Simple Auth with PostgreSQL"}
