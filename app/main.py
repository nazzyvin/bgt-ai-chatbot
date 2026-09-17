from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, health
from app.core.logging_config import configure_logging

configure_logging()

app = FastAPI(title="BGT AI Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # add your PHP site's URL here later
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(auth.router)