import logging

from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_service import LLMServiceError, generate_reply

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    logger.info("Received chat message: %s", request.message)

    try:
        reply = generate_reply(request.message)
    except LLMServiceError as exc:
        logger.error("Chat request failed: %s", exc)
        raise HTTPException(status_code=502, detail="The assistant is temporarily unavailable.") from exc

    return ChatResponse(reply=reply)