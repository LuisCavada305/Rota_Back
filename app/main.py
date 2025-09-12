from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import trails
from app.routes.auth import router as auth_router
from app.routes.me import router as me_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],)

app.include_router(trails.router, prefix="/trails", tags=["trails"])
app.include_router(auth_router)
app.include_router(me_router)