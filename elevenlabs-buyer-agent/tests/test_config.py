"""Tests for agent configuration."""

import json

from src.agent_config import build_agent_config, _build_tools, _build_evaluation_criteria
from src.prompts import get_system_prompt, get_first_message_inbound
from config.settings import Settings


def test_system_prompt_includes_agency_name():
    prompt = get_system_prompt("Test Agency Co")
    assert "Test Agency Co" in prompt
    assert "Ava" in prompt
    assert "Australian" in prompt


def test_system_prompt_includes_interview_sections():
    prompt = get_system_prompt()
    assert "Budget & Finance" in prompt
    assert "Location" in prompt
    assert "Property" in prompt
    assert "Investment" in prompt
    assert "Lifestyle" in prompt
    assert "Buying Process" in prompt


def test_system_prompt_includes_guardrails():
    prompt = get_system_prompt()
    assert "NEVER" in prompt
    assert "financial advice" in prompt.lower()
    assert "legal advice" in prompt.lower()


def test_first_message_inbound():
    msg = get_first_message_inbound("Sydney Buyers Co")
    assert "Sydney Buyers Co" in msg
    assert "Ava" in msg


def test_build_agent_config_structure():
    settings = Settings(
        elevenlabs_api_key="test",
        agency_name="Test Agency",
        elevenlabs_llm_model="claude-3-5-sonnet",
    )
    config = build_agent_config(settings)

    assert "conversational_config" in config
    assert "platform_settings" in config
    assert "name" in config

    conv_config = config["conversational_config"]
    assert "agent" in conv_config
    assert "asr" in conv_config
    assert "tts" in conv_config
    assert "turn" in conv_config


def test_tools_include_save_brief_when_webhook_configured():
    settings = Settings(
        elevenlabs_api_key="test",
        webhook_url="https://example.com/api/briefs",
        webhook_secret="secret123",
    )
    tools = _build_tools(settings)

    tool_names = [t["name"] for t in tools]
    assert "save_buyer_brief" in tool_names


def test_tools_include_system_tools():
    settings = Settings(elevenlabs_api_key="test")
    tools = _build_tools(settings)

    tool_names = [t["name"] for t in tools]
    assert "transfer_to_human" in tool_names
    assert "end_call" in tool_names


def test_evaluation_criteria_count():
    criteria = _build_evaluation_criteria()
    # Should have 5 evaluation criteria
    assert len(criteria) == 5

    # Check expected criteria exist
    ids = [c["id"] for c in criteria]
    assert "brief_completeness" in ids
    assert "customer_satisfaction" in ids
    assert "stayed_on_topic" in ids


def test_agent_config_serializable():
    settings = Settings(
        elevenlabs_api_key="test",
        webhook_url="https://example.com/api/briefs",
    )
    config = build_agent_config(settings)

    # Should be JSON serializable
    json_str = json.dumps(config)
    assert json_str
    assert "Buyer Brief Agent" in json_str
