from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.message import Message

MAX_HISTORY_MESSAGES = 20


def save_message(db: Session, conversation_id: str, role: str, content: str) -> Message:
    message = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(message)
    return message


def get_recent_messages(db: Session, conversation_id: str, limit: int = MAX_HISTORY_MESSAGES) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = db.execute(stmt).scalars().all()
    return list(reversed(messages))  # oldest first, for sending to the LLM


def get_all_messages_ordered(db: Session, conversation_id: str) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())
