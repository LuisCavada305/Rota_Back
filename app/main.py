from fastapi import FastAPI
from app.routes import trails

app = FastAPI()
app.include_router(trails.router)