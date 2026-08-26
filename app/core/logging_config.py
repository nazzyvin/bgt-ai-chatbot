import logging
import sys


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )

    # Quiet down noisy third-party logs we don't need to see
    logging.getLogger("google_genai").setLevel(logging.ERROR)