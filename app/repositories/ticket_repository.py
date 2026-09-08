from sqlalchemy.orm import Session

from app.models.ticket import Ticket


def save_ticket(db: Session, conversation_id: str, subject: str, description: str, status: str = "pending_confirmation") -> Ticket:
    ticket = Ticket(conversation_id=conversation_id, subject=subject, description=description, status=status)
    db.add(ticket)
    db.flush()
    return ticket


def get_ticket(db: Session, ticket_id: str) -> Ticket | None:
    return db.get(Ticket, ticket_id)


def get_pending_ticket(db: Session, conversation_id: str) -> Ticket | None:
    return (
        db.query(Ticket)
        .filter(Ticket.conversation_id == conversation_id, Ticket.status == "pending_confirmation")
        .order_by(Ticket.created_at.desc())
        .first()
    )


def confirm_ticket(db: Session, ticket_id: str) -> Ticket | None:
    ticket = get_ticket(db, ticket_id)
    if ticket is None:
        return None
    ticket.status = "open"
    db.add(ticket)
    return ticket