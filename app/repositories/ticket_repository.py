from sqlalchemy.orm import Session

from app.models.ticket import Ticket


def save_ticket(db: Session, conversation_id: str, subject: str, description: str) -> Ticket:
    ticket = Ticket(conversation_id=conversation_id, subject=subject, description=description)
    db.add(ticket)
    db.flush()
    return ticket