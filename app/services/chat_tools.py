import logging

from sqlalchemy.orm import Session

from app.repositories.ticket_repository import confirm_ticket as confirm_ticket_repo
from app.repositories.ticket_repository import get_pending_ticket, save_ticket

logger = logging.getLogger(__name__)


def build_tools(db: Session, conversation_id: str) -> list:
    """
    Returns the list of tool functions available to the LLM for this request.
    Built per-request (via closure) so each tool has access to this request's
    db session and conversation_id without exposing them to the LLM itself.
    """

    def create_ticket(subject: str, description: str) -> dict:
        """Draft a support ticket for the user to review. This does NOT finalize
        the ticket - it must be confirmed with confirm_ticket after the user
        explicitly agrees to the summary.

        Args:
            subject: A short summary of the issue (a few words).
            description: Full details of what the user needs help with.
        """
        if not subject.strip() or not description.strip():
            return {"error": "subject and description must not be empty"}

        try:
            ticket = save_ticket(db, conversation_id, subject.strip(), description.strip())
        except Exception:
            logger.exception("Failed to draft ticket")
            return {"error": "failed to draft ticket"}

        logger.info("Tool call: create_ticket (pending) -> ticket_id=%s subject=%s", ticket.id, subject)
        return {
            "ticket_id": ticket.id,
            "status": "pending_confirmation",
            "note": "Show this summary to the user and ask them to confirm before calling confirm_ticket.",
        }

    def confirm_ticket(ticket_id: str) -> dict:
        """Finalize a previously drafted support ticket. Only call this after
        the user has explicitly confirmed they want the ticket created.

        Args:
            ticket_id: The ID returned by create_ticket.
        """
        ticket = confirm_ticket_repo(db, ticket_id)
        if ticket is None:
            return {"error": "ticket not found"}

        logger.info("Tool call: confirm_ticket -> ticket_id=%s", ticket.id)
        return {"ticket_id": ticket.id, "status": "open"}

    tools = [create_ticket]

    if get_pending_ticket(db, conversation_id) is not None:
        tools.append(confirm_ticket)

    return tools