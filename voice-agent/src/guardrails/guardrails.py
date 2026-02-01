"""Conversation guardrails for the buyer-brief interview agent.

These run *before* user input reaches Claude and *after* Claude responds,
providing defence-in-depth beyond the system prompt instructions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class GuardrailAction(str, Enum):
    ALLOW = "allow"
    WARN = "warn"          # let through but flag for review
    BLOCK = "block"        # replace with safe message
    TERMINATE = "terminate" # end the call


@dataclass
class GuardrailResult:
    action: GuardrailAction
    reason: Optional[str] = None
    replacement_text: Optional[str] = None


# ---------------------------------------------------------------------------
# Input guardrails (user speech → before Claude)
# ---------------------------------------------------------------------------

_SENSITIVE_PATTERNS = [
    (r"\b\d{8,9}\b", "Possible TFN detected"),                 # Australian TFN
    (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "Credit card number detected"),
    (r"\bBSB\b.*\d{6}", "Bank BSB detected"),
    (r"\b\d{3}[\s-]?\d{3}[\s-]?\d{3}\b", "Possible account number detected"),
]

_ABUSE_PATTERNS = [
    r"\b(fuck|shit|cunt|bitch|asshole)\b",
]

_OFF_TOPIC_KEYWORDS = [
    "crypto", "bitcoin", "stock tips", "gambling", "betting",
    "what are you wearing", "are you single", "go out with me",
]


def check_user_input(text: str, consecutive_off_topic: int = 0) -> GuardrailResult:
    """Check user speech before sending to Claude."""
    lower = text.lower()

    # Block sensitive data
    for pattern, reason in _SENSITIVE_PATTERNS:
        if re.search(pattern, text):
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason=reason,
                replacement_text=(
                    "I noticed you might be sharing sensitive personal information. "
                    "For your security, I won't record that. "
                    "Could we get back to your property search?"
                ),
            )

    # Warn on abuse
    for pattern in _ABUSE_PATTERNS:
        if re.search(pattern, lower):
            if consecutive_off_topic >= 2:
                return GuardrailResult(
                    action=GuardrailAction.TERMINATE,
                    reason="Repeated abusive language",
                    replacement_text=(
                        "I appreciate your time, but I think it's best if I hand this "
                        "over to one of our human agents. They'll be in touch. Goodbye!"
                    ),
                )
            return GuardrailResult(
                action=GuardrailAction.WARN,
                reason="Abusive language detected",
            )

    # Track off-topic
    if any(kw in lower for kw in _OFF_TOPIC_KEYWORDS):
        if consecutive_off_topic >= 2:
            return GuardrailResult(
                action=GuardrailAction.TERMINATE,
                reason="Persistent off-topic conversation",
                replacement_text=(
                    "It seems like now might not be the best time. "
                    "Feel free to call us back when you're ready to chat about property. "
                    "Have a great day!"
                ),
            )
        return GuardrailResult(
            action=GuardrailAction.WARN,
            reason="Off-topic content",
        )

    return GuardrailResult(action=GuardrailAction.ALLOW)


# ---------------------------------------------------------------------------
# Output guardrails (Claude response → before TTS)
# ---------------------------------------------------------------------------

_PROHIBITED_OUTPUT_PATTERNS = [
    (r"(?i)\b(I guarantee|I promise|guaranteed)\b", "Guarantee language detected"),
    (r"(?i)\b(financial advice|legal advice|tax advice)\b.*\b(is|would be|should)\b",
     "Giving professional advice"),
    (r"(?i)\b(you should invest in|buy this stock|put your money)\b",
     "Investment advice detected"),
    (r"\$\d{1,3}(,\d{3})*\s*(per sqm|psm|median)",
     "Specific valuation detected"),
]


def check_agent_output(text: str) -> GuardrailResult:
    """Check Claude's response before sending to TTS."""
    for pattern, reason in _PROHIBITED_OUTPUT_PATTERNS:
        if re.search(pattern, text):
            return GuardrailResult(
                action=GuardrailAction.WARN,
                reason=reason,
            )
    return GuardrailResult(action=GuardrailAction.ALLOW)


# ---------------------------------------------------------------------------
# Call-level guardrails
# ---------------------------------------------------------------------------

def check_call_duration(elapsed_seconds: float, max_seconds: float) -> GuardrailResult:
    """Enforce maximum call duration."""
    if elapsed_seconds >= max_seconds:
        return GuardrailResult(
            action=GuardrailAction.TERMINATE,
            reason=f"Call duration exceeded {max_seconds}s limit",
            replacement_text=(
                "We've been chatting for a while! Let me save everything we've covered "
                "and one of our agents will follow up with you. Thanks for your time!"
            ),
        )
    if elapsed_seconds >= max_seconds * 0.9:
        return GuardrailResult(
            action=GuardrailAction.WARN,
            reason="Approaching call duration limit",
        )
    return GuardrailResult(action=GuardrailAction.ALLOW)
