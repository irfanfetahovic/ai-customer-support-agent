import re
import uuid
from typing import Optional

from openai import AsyncOpenAI

from src.config import INPUT_MAX_LENGTH, INJECTION_PATTERNS

# Pre-compiled regex for injection detection (zero cost at call time).
# Tier 1 focuses on prompt injection; Tier 3 (Moderation API) focuses on harmful content.
_INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

# OpenAI Moderation API client (Tier 3) — initialized lazily so importing this
# module does not require OPENAI_API_KEY to be set (e.g. during unit tests).
_moderation_client: AsyncOpenAI | None = None


def _get_moderation_client() -> AsyncOpenAI:
    global _moderation_client
    if _moderation_client is None:
        _moderation_client = AsyncOpenAI()
    return _moderation_client


def check_input_guardrails(message: str) -> Optional[str]:
    """
    Apply rule-based input guardrails (Tier 1). Returns an error string if the
    message should be blocked, or None if it passes all checks.
    """
    # Guard 1: empty input
    if not message or not message.strip():
        return "Please describe your issue or question."

    # Guard 2: message too long — cap to prevent token-stuffing
    if len(message) > INPUT_MAX_LENGTH:
        return (
            f"Your message is too long ({len(message)} characters). "
            f"Please keep it under {INPUT_MAX_LENGTH} characters."
        )

    # Guard 3: prompt injection patterns
    if _INJECTION_RE.search(message):
        return (
            "Your message contains content that cannot be processed. "
            "Please describe your support issue and I'll be happy to help."
        )

    return None  # all checks passed


async def check_moderation(text: str) -> Optional[str]:
    """
    Call the OpenAI Moderation API (Tier 3). Returns a block reason string if
    the text is flagged for harmful content, or None if it is safe.
    """
    result = await _get_moderation_client().moderations.create(input=text)
    output = result.results[0]
    if output.flagged:
        flagged_cats = [cat for cat, flagged in output.categories if flagged]
        return (
            "Your message could not be processed because it was flagged for: "
            f"{', '.join(flagged_cats)}. Please rephrase your support request."
        )
    return None  # content is safe


def make_thread_id() -> str:
    return str(uuid.uuid4())
