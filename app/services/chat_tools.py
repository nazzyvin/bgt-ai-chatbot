import logging

from sqlalchemy.orm import Session

from app.repositories.ticket_repository import save_ticket

logger = logging.getLogger(__name__)

def build_tools(db: Session, conversation_id:str) -> list:
    """
    Returns the list of tool functions available to the LLM for this request.
    Built per-request (via closure) so each tool has access to this request's
    db session and conversation_id without exposing them to the LLM itself.
    """

    def create_ticket(subject: str, description: str) -> dict:
        """Create a support ticket to escalate an issue for a team member to follow up on.

        Args:
            subject: A short summary of the issue (a few words).
            description: Full details of what the user needs help with.
        """    

        if not subject.strip() or not description.strip():
            return {"error": "subject and description must not be empty"}

        try:
            ticket = save_ticket(db, conversation_id, subject.strip(), description.strip())
        except Exception:
            logger.exception("Failed to create ticket")
            return {"error": "failed to create ticket"}

        logger.info("Tool call: create_ticket -> ticket_id=%s subject=%s", ticket.id, subject)
        return {"ticket_id": ticket.id, "status": "created"}

    return [create_ticket]
