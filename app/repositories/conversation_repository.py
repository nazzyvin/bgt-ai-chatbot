import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConversationAccessDeniedError,
    ConversationExpiredError,
    ConversationNotFoundError,
)
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.repositories.message_repository import get_all_messages_ordered
from app.services.llm_service import summarize_messages

CONVERSATION_EXPIRY_HOURS = int(os.getenv("CONVERSATION_EXPIRY_HOURS", 168))
KEEP_RECENT_MESSAGES = 20
SUMMARIZE_THRESHOLD = 30  # only summarize once conversation is meaningfully long


def is_expired(db: Session, conversation: Conversation) -> bool:
    latest_message = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .first()
    )
    reference_time = latest_message.created_at if latest_message else conversation.created_at
    if reference_time is None:
        return False

    reference_time = reference_time.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - reference_time > timedelta(hours=CONVERSATION_EXPIRY_HOURS)


def get_conversation(db: Session, conversation_id: str) -> Conversation | None:
    return db.get(Conversation, conversation_id)


def create_conversation(db: Session, user_id: str | None = None) -> Conversation:
    conversation = Conversation(user_id=user_id)
    db.add(conversation)
    db.flush()
    return conversation


def authorize_conversation_access(
    conversation: Conversation, current_user: User | None, allow_staff_override: bool = True
) -> None:
    """
    Raises ConversationAccessDeniedError if current_user may not access this
    conversation.
      - conversation.user_id is None (legacy/anonymous) -> anyone may access
      - conversation belongs to current_user -> allowed
      - current_user is admin -> always allowed
      - current_user is staff -> allowed only if allow_staff_override is True
        (continuing a conversation for support use, not deletion)
      - otherwise -> denied
    """
    if conversation.user_id is None:
        return
    if current_user is not None and conversation.user_id == current_user.id:
        return
    if current_user is not None and current_user.role == "admin":
        return
    if current_user is not None and current_user.role == "staff" and allow_staff_override:
        return
    raise ConversationAccessDeniedError(f"Access denied to conversation: {conversation.id}")


def get_or_create_conversation(
    db: Session, conversation_id: str | None, current_user: User | None = None
) -> Conversation:
    if conversation_id:
        conversation = get_conversation(db, conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(f"Conversation not found: {conversation_id}")

        authorize_conversation_access(conversation, current_user)

        if is_expired(db, conversation):
            raise ConversationExpiredError(f"Conversation expired: {conversation_id}")

        return conversation

    return create_conversation(db, user_id=current_user.id if current_user else None)


def delete_conversation(db: Session, conversation_id: str) -> bool:
    conversation = get_conversation(db, conversation_id)
    if conversation is None:
        return False
    db.delete(conversation)
    return True


def maybe_summarize_conversation(db: Session, conversation: Conversation) -> None:
    all_messages = get_all_messages_ordered(db, conversation.id)
    total = len(all_messages)

    if total <= SUMMARIZE_THRESHOLD:
        return

    already_summarized = conversation.summarized_message_count
    messages_to_summarize = all_messages[already_summarized: total - KEEP_RECENT_MESSAGES]

    if not messages_to_summarize:
        return

    payload = [{"role": m.role, "content": m.content} for m in messages_to_summarize]
    conversation.summary = summarize_messages(conversation.summary, payload)
    conversation.summarized_message_count = already_summarized + len(messages_to_summarize)
    db.add(conversation)