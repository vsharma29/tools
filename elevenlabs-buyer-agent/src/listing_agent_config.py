"""ElevenLabs Listing Agent Sales Associate configuration builder.

Constructs the agent configuration for open home follow-up calls on behalf
of a listing agency (seller's agent). This agent gathers feedback from
potential buyers who attended open inspections.
"""

from __future__ import annotations

from typing import Any

from config.settings import Settings
from .listing_agent_prompts import (
    get_listing_agent_system_prompt,
    get_listing_agent_first_message_generic,
    LISTING_AGENT_DYNAMIC_VARIABLES,
)


def build_listing_agent_config(
    settings: Settings,
    voice_id: str = "LqLLaHt3jxALsSIqaKoa",  # Antonio
    agency_name: str = "Your Real Estate Agency",
) -> dict[str, Any]:
    """Build the complete ElevenLabs Listing Agent configuration.

    Args:
        settings: Application settings from environment
        voice_id: ElevenLabs voice ID (default: Antonio)
        agency_name: Name of the listing agency

    Returns:
        Configuration dict ready for ElevenLabs API
    """
    return {
        "conversation_config": _build_conversation_config(settings, voice_id, agency_name),
        "name": "Listing Agent - Open Home Follow-up",
    }


def _build_conversation_config(
    settings: Settings,
    voice_id: str,
    agency_name: str,
) -> dict[str, Any]:
    """Build the conversation_config section for the Listing Agent."""
    return {
        "agent": _build_agent_section(settings, agency_name),
        "tts": _build_tts_config(voice_id),
        "turn": _build_turn_config(),
        "conversation": _build_conversation_limits(),
    }


def _build_agent_section(settings: Settings, agency_name: str) -> dict[str, Any]:
    """Build the agent section with prompt, tools, and first message."""
    first_message = get_listing_agent_first_message_generic(agency_name)

    return {
        "first_message": first_message,
        "language": "en",
        "dynamic_variables": {
            "prospect_name": "there",
            "property_address": "",
            "inspection_date": "the weekend",
            "agency_name": agency_name,
        },
        "prompt": {
            "prompt": get_listing_agent_system_prompt(agency_name),
            "llm": "gpt-4o",  # Best for natural conversation
            "temperature": 0.9,  # Higher for more natural variation
            "max_tokens": 150,  # Short responses only
        },
        "tools": _build_tools(settings),
    }


def _build_tools(settings: Settings) -> list[dict[str, Any]]:
    """Build the tools configuration for the Listing Agent."""
    tools = []

    # Webhook tool to save open home feedback
    if settings.has_webhook:
        tools.append({
            "type": "webhook",
            "name": "save_open_home_feedback",
            "description": (
                "Save the feedback from the open home follow-up call. Call this at the end "
                "of the conversation to record the buyer's interest level, feedback, and preferences."
            ),
            "webhook": {
                "url": settings.webhook_url,
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json",
                    "X-Webhook-Secret": settings.webhook_secret,
                    "X-Agent-Type": "listing-agent",
                },
                "request_body_schema": {
                    "type": "object",
                    "properties": {
                        "feedback": {
                            "type": "object",
                            "description": "Feedback from the open home follow-up call",
                            "properties": {
                                "prospect_name": {"type": "string"},
                                "prospect_phone": {"type": "string"},
                                "property_address": {"type": "string"},
                                "interest_level": {
                                    "type": "string",
                                    "enum": ["hot", "warm", "cool", "not_interested"],
                                },
                                "perceived_value": {
                                    "type": "string",
                                    "description": "What the buyer thinks the property is worth",
                                },
                                "budget_range": {"type": "string"},
                                "what_they_liked": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "what_they_didnt_like": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "buying_position": {
                                    "type": "string",
                                    "description": "Finance status, ready to proceed, etc.",
                                },
                                "private_inspection_requested": {"type": "boolean"},
                                "preferred_contact_method": {
                                    "type": "string",
                                    "enum": ["phone", "email", "sms"],
                                },
                                "notes": {"type": "string"},
                            },
                        }
                    },
                    "required": ["feedback"],
                },
            },
            "response_timeout_secs": 10,
        })

    # Tool to schedule private inspection
    tools.append({
        "type": "system",
        "name": "schedule_private_inspection",
        "description": (
            "Schedule a private inspection for an interested buyer. Use when they "
            "want to see the property again without the open home crowds."
        ),
        "system_tool_type": "end_call",
    })

    # System tool for ending the call gracefully
    tools.append({
        "type": "system",
        "name": "end_call",
        "description": (
            "End the call gracefully after gathering feedback, "
            "or when the prospect wants to end the conversation."
        ),
        "system_tool_type": "end_call",
    })

    return tools


def _build_tts_config(voice_id: str) -> dict[str, Any]:
    """Build the TTS configuration for natural human-like speech.

    Voice settings optimized to sound human, not robotic:
    - Lower stability (0.3-0.4): More expressive, natural variation
    - Higher similarity_boost (0.8): Maintains voice character
    - Model: eleven_turbo_v2 for English
    """
    return {
        "model_id": "eleven_turbo_v2",  # Required for English agents
        "voice_id": voice_id,
        "stability": 0.35,  # Lower = more expressive, natural variation
        "similarity_boost": 0.80,  # Higher = consistent voice character
        "style": 0.45,  # Add some style/emotion
        "use_speaker_boost": True,  # Enhance voice clarity
    }


def _build_turn_config() -> dict[str, Any]:
    """Build the turn-taking configuration for natural conversation."""
    return {
        "turn_timeout": 12,  # Longer timeout - let them think
        "turn_eagerness": "patient",  # Don't interrupt - let them finish
        "silence_end_call_timeout": 60,  # Longer before ending on silence
        "speculative_turn": True,  # Start processing during silence
    }


def _build_conversation_limits() -> dict[str, Any]:
    """Build the conversation limits configuration."""
    return {
        "max_duration_seconds": 480,  # 8 minutes max for follow-up calls
    }
