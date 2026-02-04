"""ElevenLabs Agent configuration builder.

Constructs the full agent configuration object for the ElevenLabs
Conversational AI platform, including:
- System prompt
- Voice settings
- LLM configuration
- Tools (webhook for saving briefs)
- Success evaluations
- Data collection criteria
- Platform settings
"""

from __future__ import annotations

from typing import Any

from config.settings import Settings
from .prompts import get_system_prompt, get_first_message_inbound, DYNAMIC_VARIABLES


def build_agent_config(settings: Settings, is_outbound: bool = False) -> dict[str, Any]:
    """Build the complete ElevenLabs agent configuration.

    Args:
        settings: Application settings from environment
        is_outbound: If True, configure for outbound calls

    Returns:
        Configuration dict ready for ElevenLabs API

    Note:
        ElevenLabs API uses 'conversation_config' (not 'conversational_config').
        English agents must use 'eleven_turbo_v2' or 'eleven_flash_v2' TTS models.
    """
    return {
        "conversation_config": _build_conversation_config_section(settings, is_outbound),
        "platform_settings": _build_platform_settings(settings),
        "name": "Buyer Brief Agent",
    }


def _build_conversation_config_section(settings: Settings, is_outbound: bool) -> dict[str, Any]:
    """Build the conversation_config section for the ElevenLabs API."""
    return {
        "agent": _build_agent_section(settings, is_outbound),
        "tts": _build_tts_config(settings),
        "turn": _build_turn_config(),
        "conversation": _build_conversation_limits(settings),
    }


def _build_agent_section(settings: Settings, is_outbound: bool) -> dict[str, Any]:
    """Build the agent section with prompt, tools, and first message."""
    first_message = get_first_message_inbound(settings.agency_name)

    agent_config = {
        "first_message": first_message,
        "language": "en",
        "dynamic_variables": [
            {"name": "prospect_name", "value": "the prospect"},
            {"name": "agency_name", "value": settings.agency_name},
        ],
        "prompt": {
            "prompt": get_system_prompt(settings.agency_name),
            "llm": settings.elevenlabs_llm_model,
            "temperature": settings.elevenlabs_llm_temperature,
            "max_tokens": 500,
        },
        "tools": _build_tools(settings),
    }

    return agent_config


def _build_tools(settings: Settings) -> list[dict[str, Any]]:
    """Build the tools configuration including webhook for saving briefs."""
    tools = []

    # Webhook tool to save the buyer brief
    if settings.has_webhook:
        tools.append({
            "type": "webhook",
            "name": "save_buyer_brief",
            "description": (
                "Save the completed buyer brief. Call this once you have gathered enough "
                "information from the prospect and confirmed the summary with them. "
                "Include all gathered information in the brief_data parameter."
            ),
            "webhook": {
                "url": settings.webhook_url,
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json",
                    "X-Webhook-Secret": settings.webhook_secret,
                },
                "request_body_schema": {
                    "type": "object",
                    "properties": {
                        "brief_data": {
                            "type": "object",
                            "description": "The complete buyer brief data",
                            "properties": {
                                "prospect_name": {"type": "string"},
                                "prospect_phone": {"type": "string"},
                                "prospect_email": {"type": "string"},
                                "purchase_purpose": {
                                    "type": "string",
                                    "enum": ["owner_occupier", "investment", "smsf", "development", "holiday_home"]
                                },
                                "budget": {
                                    "type": "object",
                                    "properties": {
                                        "min_price": {"type": "integer"},
                                        "max_price": {"type": "integer"},
                                        "stretch_budget": {"type": "integer"},
                                        "deposit_available": {"type": "integer"},
                                        "finance_status": {"type": "string"},
                                        "first_home_buyer": {"type": "boolean"},
                                        "using_fhog": {"type": "boolean"},
                                        "using_fhss": {"type": "boolean"},
                                    }
                                },
                                "location": {
                                    "type": "object",
                                    "properties": {
                                        "preferred_states": {"type": "array", "items": {"type": "string"}},
                                        "preferred_cities": {"type": "array", "items": {"type": "string"}},
                                        "preferred_suburbs": {"type": "array", "items": {"type": "string"}},
                                        "excluded_suburbs": {"type": "array", "items": {"type": "string"}},
                                        "max_commute_minutes": {"type": "integer"},
                                        "commute_destination": {"type": "string"},
                                    }
                                },
                                "property_requirements": {
                                    "type": "object",
                                    "properties": {
                                        "property_types": {"type": "array", "items": {"type": "string"}},
                                        "min_bedrooms": {"type": "integer"},
                                        "min_bathrooms": {"type": "integer"},
                                        "min_car_spaces": {"type": "integer"},
                                        "min_land_size_sqm": {"type": "integer"},
                                        "pool_preference": {"type": "string"},
                                        "condition_preference": {"type": "string"},
                                    }
                                },
                                "investment_criteria": {
                                    "type": "object",
                                    "properties": {
                                        "strategy": {"type": "string"},
                                        "target_rental_yield_pct": {"type": "number"},
                                        "target_weekly_rent": {"type": "integer"},
                                    }
                                },
                                "lifestyle": {
                                    "type": "object",
                                    "properties": {
                                        "household_composition": {"type": "string"},
                                        "school_requirements": {"type": "array", "items": {"type": "string"}},
                                        "deal_breakers": {"type": "array", "items": {"type": "string"}},
                                        "nice_to_haves": {"type": "array", "items": {"type": "string"}},
                                    }
                                },
                                "buying_process": {
                                    "type": "object",
                                    "properties": {
                                        "timeline": {"type": "string"},
                                        "auction_comfort": {"type": "string"},
                                        "current_property_to_sell": {"type": "boolean"},
                                    }
                                },
                                "agent_notes": {"type": "string"},
                            },
                        }
                    },
                    "required": ["brief_data"],
                },
            },
            "response_timeout_secs": 10,
        })

    # System tool for transferring to human agent
    tools.append({
        "type": "system",
        "name": "transfer_to_human",
        "description": (
            "Transfer the call to a human buyer's agent. Use when: "
            "the prospect requests it, the conversation goes off-topic, "
            "or the prospect becomes upset."
        ),
        "system_tool_type": "end_call",
    })

    # System tool for ending the call gracefully
    tools.append({
        "type": "system",
        "name": "end_call",
        "description": (
            "End the call gracefully after completing the interview and saving the brief, "
            "or when the prospect wants to end the conversation."
        ),
        "system_tool_type": "end_call",
    })

    return tools


def _build_asr_config() -> dict[str, Any]:
    """Build the ASR (speech recognition) configuration."""
    return {
        "provider": "elevenlabs",
        "quality": "high",
        "user_input_audio_format": "pcm_16000",
        "keywords": [
            # Australian property terms
            "FHOG", "FHSS", "pre-approval", "strata", "body corporate",
            "suburb", "Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide",
            "NSW", "VIC", "QLD", "WA", "SA", "ACT", "TAS", "NT",
            # Property types
            "townhouse", "duplex", "granny flat", "acreage",
            # Investment terms
            "negative gearing", "depreciation", "rental yield",
        ],
    }


def _build_tts_config(settings: Settings) -> dict[str, Any]:
    """Build the TTS (text-to-speech) configuration.

    Note: English agents must use 'eleven_turbo_v2' or 'eleven_flash_v2'
    (not the _5 suffix versions).
    """
    # Ensure we use a valid TTS model for English agents
    model_id = settings.elevenlabs_tts_model
    if model_id in ("eleven_turbo_v2_5", "eleven_flash_v2_5"):
        model_id = model_id.replace("_5", "")  # Use v2 instead of v2_5

    config = {
        "model_id": model_id,
        "stability": settings.elevenlabs_voice_stability,
        "similarity_boost": settings.elevenlabs_similarity_boost,
    }

    if settings.elevenlabs_voice_id:
        config["voice_id"] = settings.elevenlabs_voice_id

    return config


def _build_turn_config() -> dict[str, Any]:
    """Build the turn-taking configuration."""
    return {
        "turn_timeout": 8,  # Wait 8s for user response
        "turn_eagerness": "normal",
        "silence_end_call_timeout": 30,  # End call after 30s silence
        "speculative_turn": True,  # Start LLM during silence for lower latency
    }


def _build_conversation_limits(settings: Settings) -> dict[str, Any]:
    """Build the conversation limits configuration."""
    return {
        "max_duration_seconds": settings.max_conversation_duration,
    }


def _build_platform_settings(settings: Settings) -> dict[str, Any]:
    """Build the platform settings section."""
    return {
        "privacy": {
            "record_voice": settings.enable_recording,
            "retention_days": settings.retention_days,
        },
        "evaluation": _build_evaluation_criteria(),
        "data_collection": _build_data_collection_criteria(),
    }


def _build_evaluation_criteria() -> list[dict[str, Any]]:
    """Build success evaluation criteria for conversation analysis."""
    return [
        {
            "id": "brief_completeness",
            "type": "goal_prompt",
            "description": (
                "Evaluate if the agent gathered sufficient information for a buyer brief. "
                "Check if the following were covered: budget range, location preferences, "
                "property type requirements, and timeline. "
                "Return success if at least 3 of these 4 areas were discussed in detail."
            ),
        },
        {
            "id": "customer_satisfaction",
            "type": "goal_prompt",
            "description": (
                "Evaluate if the prospect seemed satisfied with the conversation. "
                "Check for positive indicators like agreement, thanks, or expressing "
                "excitement about working together. Check for negative indicators like "
                "frustration, confusion, or wanting to end the call early. "
                "Return success if the conversation ended positively."
            ),
        },
        {
            "id": "stayed_on_topic",
            "type": "goal_prompt",
            "description": (
                "Evaluate if the agent stayed focused on gathering buyer brief information. "
                "Return failure if the agent provided specific property valuations, "
                "gave legal or financial advice, or went significantly off-topic. "
                "Return success if the agent maintained appropriate boundaries."
            ),
        },
        {
            "id": "brief_saved",
            "type": "goal_prompt",
            "description": (
                "Evaluate if the save_buyer_brief tool was called successfully. "
                "Return success if the tool was called and the brief was saved. "
                "Return failure if the conversation ended without saving the brief "
                "and the prospect was qualified."
            ),
        },
        {
            "id": "professional_tone",
            "type": "goal_prompt",
            "description": (
                "Evaluate if the agent maintained a professional yet friendly tone "
                "throughout the conversation. Check for Australian English conventions, "
                "appropriate warmth, and clear communication. "
                "Return success if the tone was consistently professional."
            ),
        },
    ]


def _build_data_collection_criteria() -> list[dict[str, Any]]:
    """Build data collection criteria for extracting structured info from conversations."""
    return [
        {
            "id": "prospect_contact",
            "description": "Extract the prospect's contact information: name, phone, email",
            "json_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "email": {"type": "string"},
                    "preferred_contact_method": {"type": "string"},
                }
            }
        },
        {
            "id": "budget_summary",
            "description": "Extract budget information: price range, finance status, first home buyer",
            "json_schema": {
                "type": "object",
                "properties": {
                    "min_price": {"type": "integer"},
                    "max_price": {"type": "integer"},
                    "finance_status": {"type": "string"},
                    "first_home_buyer": {"type": "boolean"},
                }
            }
        },
        {
            "id": "location_summary",
            "description": "Extract location preferences: suburbs, cities, states, exclusions",
            "json_schema": {
                "type": "object",
                "properties": {
                    "preferred_areas": {"type": "array", "items": {"type": "string"}},
                    "excluded_areas": {"type": "array", "items": {"type": "string"}},
                }
            }
        },
        {
            "id": "property_summary",
            "description": "Extract property requirements: type, beds, baths, land size",
            "json_schema": {
                "type": "object",
                "properties": {
                    "property_type": {"type": "string"},
                    "bedrooms": {"type": "integer"},
                    "land_size_sqm": {"type": "integer"},
                }
            }
        },
        {
            "id": "timeline_summary",
            "description": "Extract buying timeline and urgency",
            "json_schema": {
                "type": "object",
                "properties": {
                    "timeline": {"type": "string"},
                    "ready_to_proceed": {"type": "boolean"},
                }
            }
        },
    ]
