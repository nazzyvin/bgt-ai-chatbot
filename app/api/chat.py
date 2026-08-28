import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.conversation_repository import get_or_create_conversation
from app.repositories.message_repository import save_message
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_service import LLMServiceError, generate_reply

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    logger.info("Received chat message: %s", request.message)

    try:
        conversation = get_or_create_conversation(db, request.conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found.") from exc

    save_message(db, conversation.id, role="user", content=request.message)

    try:
        reply_text = generate_reply(request.message)
    except LLMServiceError as exc:
        logger.error("Chat request failed: %s", exc)
        db.rollback()
        raise HTTPException(status_code=502, detail="The assistant is temporarily unavailable.") from exc

    save_message(db, conversation.id, role="assistant", content=reply_text)

    db.commit()

    return ChatResponse(reply=reply_text, conversation_id=conversation.id)