import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message
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


def create_conversation(db: Session) -> Conversation:
    conversation = Conversation()
    db.add(conversation)
    db.flush()  # assigns conversation.id without committing yet
    return conversation


def get_or_create_conversation(db: Session, conversation_id: str | None) -> Conversation:
    if conversation_id:
        conversation = get_conversation(db, conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation not found: {conversation_id}")
        if is_expired(db, conversation):
            raise ValueError(f"Conversation expired: {conversation_id}")
        return conversation

    return create_conversation(db)


def delete_conversation(db: Session, conversation_id: str) -> bool:
    conversation = get_conversation(db, conversation_id)
    if conversation is None:
        return False
    db.delete(conversation) # cascade="all, delete-orphan" on the model handles the messages
    return True


def maybe_summarize_conversation(db: Session, conversation: Conversation) -> None:
    all_messages = get_all_messages_ordered(db, conversation.id)
    total = len(all_messages)

    if total <= SUMMARIZE_THRESHOLD:
        return  # not long enough yet, nothing to do

    already_summarized = conversation.summarized_message_count
    messages_to_summarize = all_messages[already_summarized: total - KEEP_RECENT_MESSAGES]

    if not messages_to_summarize:
        return  # nothing new to fold in

    payload = [{"role": m.role, "content": m.content} for m in messages_to_summarize]
    conversation.summary = summarize_messages(conversation.summary, payload)
    conversation.summarized_message_count = already_summarized + len(messages_to_summarize)
    db.add(conversation)