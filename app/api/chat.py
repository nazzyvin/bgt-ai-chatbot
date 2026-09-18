import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional
from app.core.exceptions import (
    ConversationAccessDeniedError,
    ConversationExpiredError,
    ConversationNotFoundError,
)
from app.db.session import get_db
from app.models.user import User
from app.repositories.conversation_repository import (
    authorize_conversation_access,
    delete_conversation,
    get_conversation,
    get_or_create_conversation,
    maybe_summarize_conversation,
)
from app.repositories.message_repository import get_recent_messages, save_message
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_tools import build_tools
from app.services.llm_service import LLMServiceError, generate_reply

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    logger.info("Received chat message: %s", request.message)

    try:
        conversation = get_or_create_conversation(db, request.conversation_id, current_user)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found.") from exc
    except ConversationAccessDeniedError as exc:
        raise HTTPException(status_code=403, detail="You do not have access to this conversation.") from exc
    except ConversationExpiredError as exc:
        raise HTTPException(status_code=410, detail="This conversation has expired. Please start a new one.") from exc

    save_message(db, conversation.id, role="user", content=request.message)
    db.flush()

    maybe_summarize_conversation(db, conversation)

    history = get_recent_messages(db, conversation.id)
    history_payload = [{"role": m.role, "content": m.content} for m in history]

    tools = build_tools(db, conversation.id, current_user)

    try:
        reply_text = generate_reply(history_payload, summary=conversation.summary, tools=tools)
    except LLMServiceError as exc:
        logger.error("Chat request failed: %s", exc)
        db.rollback()
        raise HTTPException(status_code=502, detail="The assistant is temporarily unavailable.") from exc

    save_message(db, conversation.id, role="assistant", content=reply_text)

    db.commit()

    return ChatResponse(reply=reply_text, conversation_id=conversation.id)


@router.delete("/conversations/{conversation_id}")
def reset_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    conversation = get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    try:
        authorize_conversation_access(conversation, current_user, allow_staff_override=False)
    except ConversationAccessDeniedError as exc:
        raise HTTPException(status_code=403, detail="You do not have access to this conversation.") from exc

    delete_conversation(db, conversation_id)
    db.commit()
    return {"status": "deleted", "conversation_id": conversation_id}