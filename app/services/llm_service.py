import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

load_dotenv()

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


class LLMServiceError(Exception):
    """Raised when the LLM provider call fails."""


BASE_SYSTEM_INSTRUCTION = (
    "You are a helpful assistant for the company's chatbot. "
    "You have two tools for support tickets: create_ticket drafts a ticket and "
    "returns a summary - you must show that summary to the user and ask them to "
    "confirm before doing anything else. Only call confirm_ticket after the user "
    "has clearly said yes/confirmed in their own words. Never call confirm_ticket "
    "in the same turn as create_ticket." 
)


def generate_reply(history: list[dict], summary: str | None = None, tools: list | None = None) -> str:
    """
    history: list of {"role": "user"|"assistant", "content": str}, oldest first.
    summary: optional running summary of older messages not included in history.
    tools: optional list of plain Python functions the model may call (automatic
        function calling - the SDK executes them and returns the final text).
    """
    contents = [
        {
            "role": "user" if msg["role"] == "user" else "model",
            "parts": [{"text": msg["content"]}],
        }
        for msg in history
    ]

    system_instruction = BASE_SYSTEM_INSTRUCTION
    if summary:
        system_instruction += f"\n\nEarlier conversation summary: {summary}"
    
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools
    )

    try:
        response = _client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config=config,
        )
    except genai_errors.APIError as exc:
        logger.exception("Gemini API call failed")
        raise LLMServiceError(f"LLM provider call failed: {exc}") from exc

    if not response.text:
        raise LLMServiceError("LLM returned an empty response")

    return response.text


def summarize_messages(existing_summary: str | None, messages_to_summarize: list[dict]) -> str:
    """
    Condense older messages into a short running summary.
    existing_summary: prior summary text, if any (so we extend it, not restart it).
    messages_to_summarize: list of {"role": ..., "content": ...} to fold in.
    """
    conversation_text = "\n".join(
        f"{msg['role']}: {msg['content']}" for msg in messages_to_summarize
    )

    prompt = (
        "Summarize the following conversation excerpt in 2-4 concise sentences, "
        "preserving names, facts, and any commitments made. "
        "If a prior summary is given, extend it rather than repeating it.\n\n"
    )
    if existing_summary:
        prompt += f"Prior summary:\n{existing_summary}\n\n"
    prompt += f"New messages to fold in:\n{conversation_text}"

    try:
        response = _client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
    except genai_errors.APIError as exc:
        logger.exception("Summarization call failed")
        raise LLMServiceError(f"Summarization call failed: {exc}") from exc

    return response.text.strip() if response.text else existing_summary or ""
