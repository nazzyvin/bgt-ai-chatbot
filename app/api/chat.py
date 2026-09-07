import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.conversation_repository import (
    delete_conversation,
    get_or_create_conversation,
    maybe_summarize_conversation,
)
from app.repositories.message_repository import get_recent_messages, save_message
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
        if "expired" in str(exc):
            raise HTTPException(status_code=410, detail="This conversation has expired. Please start a new one.") from exc
        raise HTTPException(status_code=404, detail="Conversation not found.") from exc

    save_message(db, conversation.id, role="user", content=request.message)
    db.flush()  # so the message we just saved is included in the history fetch below

    maybe_summarize_conversation(db, conversation)

    history = get_recent_messages(db, conversation.id)
    history_payload= [{"role": m.role, "content": m.content} for m in history]

    try:
        reply_text = generate_reply(history_payload, summary=conversation.summary)
    except LLMServiceError as exc:
        logger.error("Chat request failed: %s", exc)
        db.rollback()
        raise HTTPException(status_code=502, detail="The assistant is temporarily unavailable.") from exc

    save_message(db, conversation.id, role="assistant", content=reply_text)

    db.commit()

    return ChatResponse(reply=reply_text, conversation_id=conversation.id)


@router.delete("/conversations/{conversation_id}")
def reset_conversation(conversation_id: str, db: Session = Depends(get_db)):
    deleted = delete_conversation(db, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    db.commit()
    return {"status": "deleted", "conversation_id": conversation_id}