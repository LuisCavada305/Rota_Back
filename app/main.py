from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import trails, user_trails
from app.routes.auth import router as auth_router
from app.routes.me import router as me_router
from app.routes import trail_items  

app = FastAPI(swagger_ui_parameters={"defaultModelsExpandDepth": -1})

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",  # se abrir o front por 127.0.0.1
    "https://localhost:5173",  # se usar https no front
    "https://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trail_items.router)
app.include_router(trails.router)
app.include_router(auth_router)
app.include_router(me_router)
app.include_router(user_trails.router)
