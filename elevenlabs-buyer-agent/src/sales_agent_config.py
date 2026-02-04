"""ElevenLabs Sales Associate Agent configuration builder.

Constructs the agent configuration for follow-up calls with prospects
who have shown interest in properties through various channels.
"""

from __future__ import annotations

from typing import Any

from config.settings import Settings
from .sales_prompts import (
    get_sales_system_prompt,
    get_sales_first_message_generic,
    SALES_DYNAMIC_VARIABLES,
)


def build_sales_agent_config(settings: Settings) -> dict[str, Any]:
    """Build the complete ElevenLabs Sales Associate agent configuration.

    Args:
        settings: Application settings from environment

    Returns:
        Configuration dict ready for ElevenLabs API
    """
    return {
        "conversation_config": _build_conversation_config(settings),
        "platform_settings": _build_platform_settings(settings),
        "name": "Sales Associate Agent",
    }


def _build_conversation_config(settings: Settings) -> dict[str, Any]:
    """Build the conversation_config section for the Sales Associate."""
    return {
        "agent": _build_agent_section(settings),
        "tts": _build_tts_config(settings),
        "turn": _build_turn_config(),
        "conversation": _build_conversation_limits(settings),
    }


def _build_agent_section(settings: Settings) -> dict[str, Any]:
    """Build the agent section with prompt, tools, and first message."""
    first_message = get_sales_first_message_generic(settings.agency_name)

    return {
        "first_message": first_message,
        "language": "en",
        "dynamic_variables": {
            "prospect_name": "there",
            "property_address": "",
            "interest_source": "",
            "days_since_enquiry": "",
            "agency_name": settings.agency_name,
        },
        "prompt": {
            "prompt": get_sales_system_prompt(settings.agency_name),
            "llm": settings.sales_llm_model or settings.elevenlabs_llm_model,
            "temperature": 0.7,  # Slightly higher for more natural conversation
            "max_tokens": 500,
        },
        "tools": _build_tools(settings),
    }


def _build_tools(settings: Settings) -> list[dict[str, Any]]:
    """Build the tools configuration for the Sales Associate."""
    tools = []

    # Webhook tool to save lead outcome
    if settings.has_webhook:
        tools.append({
            "type": "webhook",
            "name": "save_lead_outcome",
            "description": (
                "Save the outcome of the sales call. Call this at the end of the conversation "
                "to record the lead's interest level, requirements, and next steps."
            ),
            "webhook": {
                "url": settings.webhook_url,
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json",
                    "X-Webhook-Secret": settings.webhook_secret,
                    "X-Agent-Type": "sales-associate",
                },
                "request_body_schema": {
                    "type": "object",
                    "properties": {
                        "lead_outcome": {
                            "type": "object",
                            "description": "The outcome of the sales follow-up call",
                            "properties": {
                                "prospect_name": {"type": "string"},
                                "prospect_phone": {"type": "string"},
                                "interest_level": {
                                    "type": "string",
                                    "enum": ["hot", "warm", "cool", "not_interested"],
                                    "description": "How interested is the prospect"
                                },
                                "property_discussed": {"type": "string"},
                                "requirements_summary": {"type": "string"},
                                "timeline": {"type": "string"},
                                "finance_status": {"type": "string"},
                                "next_steps": {"type": "string"},
                                "preferred_contact_method": {
                                    "type": "string",
                                    "enum": ["phone", "email", "sms"]
                                },
                                "follow_up_date": {"type": "string"},
                                "notes": {"type": "string"},
                                "reason_not_interested": {"type": "string"},
                            },
                        }
                    },
                    "required": ["lead_outcome"],
                },
            },
            "response_timeout_secs": 10,
        })

    # Tool to transfer to buyer's agent for hot leads
    tools.append({
        "type": "system",
        "name": "transfer_to_buyers_agent",
        "description": (
            "Transfer the call to a buyer's agent for hot leads who want to discuss "
            "a specific property or are ready to proceed with a consultation."
        ),
        "system_tool_type": "end_call",
    })

    # Tool to schedule a callback
    tools.append({
        "type": "system",
        "name": "schedule_callback",
        "description": (
            "Schedule a callback for a later time when the prospect is busy but interested."
        ),
        "system_tool_type": "end_call",
    })

    # System tool for ending the call gracefully
    tools.append({
        "type": "system",
        "name": "end_call",
        "description": (
            "End the call gracefully after completing the follow-up, "
            "or when the prospect wants to end the conversation."
        ),
        "system_tool_type": "end_call",
    })

    return tools


def _build_tts_config(settings: Settings) -> dict[str, Any]:
    """Build the TTS configuration for the Sales Associate.

    Note: English agents must use 'eleven_turbo_v2' or 'eleven_flash_v2'
    (not the _5 suffix versions).
    """
    # Use a different voice for the sales associate if configured
    voice_id = settings.sales_voice_id or settings.elevenlabs_voice_id

    # Ensure we use a valid TTS model for English agents
    model_id = settings.elevenlabs_tts_model
    if model_id in ("eleven_turbo_v2_5", "eleven_flash_v2_5"):
        model_id = model_id.replace("_5", "")  # Use v2 instead of v2_5

    config = {
        "model_id": model_id,
        "stability": 0.6,  # Slightly more expressive
        "similarity_boost": 0.75,
    }

    if voice_id:
        config["voice_id"] = voice_id

    return config


def _build_turn_config() -> dict[str, Any]:
    """Build the turn-taking configuration."""
    return {
        "turn_timeout": 10,  # Longer timeout for sales calls
        "turn_eagerness": "normal",
        "silence_end_call_timeout": 45,  # Longer silence tolerance
        "speculative_turn": True,
    }


def _build_conversation_limits(settings: Settings) -> dict[str, Any]:
    """Build the conversation limits configuration."""
    return {
        "max_duration_seconds": 600,  # 10 minutes max for follow-up calls
    }


def _build_platform_settings(settings: Settings) -> dict[str, Any]:
    """Build the platform settings section."""
    return {
        "privacy": {
            "record_voice": settings.enable_recording,
            "retention_days": settings.retention_days,
        },
        "evaluation": {
            "criteria": [
                {
                    "id": "lead_qualified",
                    "type": "prompt",
                    "prompt": (
                        "Evaluate if the agent successfully qualified the lead. "
                        "Check if interest level, timeline, and requirements were captured. "
                        "Return success if the lead was properly categorized."
                    ),
                },
                {
                    "id": "professional_tone",
                    "type": "prompt",
                    "prompt": (
                        "Evaluate if the agent maintained a friendly, professional Australian tone. "
                        "Check for natural language, appropriate warmth, and genuine helpfulness. "
                        "Return failure if the agent was pushy or used high-pressure tactics."
                    ),
                },
            ],
        },
    }
