from sqlalchemy.orm import Session

from app.models.conversation import Conversation


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
        return conversation

    return create_conversation(db)
