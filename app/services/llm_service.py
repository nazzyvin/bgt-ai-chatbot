import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors

load_dotenv()

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


class LLMServiceError(Exception):
    """Raised when the LLM provider call fails."""


def generate_reply(history: list[dict]) -> str:
    """
    history: list of {"role": "user"|"assistant", "content": str}, oldest first.
    The Gemini API expects roles "user" and "model", so we translate here.
    """
    contents = [
        {
            "role": "user" if msg["role"] == "user" else "model",
            "parts": [{"text": msg["content"]}],
        }
        for msg in history
    ]
    try:
        response = _client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents
        )
    except genai_errors.APIError as exc:
        logger.exception("Gemini API call failed")
        raise LLMServiceError(f"LLM provider call failed: {exc}") from exc

    if not response.text:
        raise LLMServiceError("LLM returned an empty response")

    return response.text