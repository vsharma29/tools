"""Tests for conversation guardrails."""

from src.guardrails.guardrails import (
    GuardrailAction,
    check_agent_output,
    check_call_duration,
    check_user_input,
)


def test_allows_normal_input():
    result = check_user_input("I'm looking for a 3 bedroom house in Sydney")
    assert result.action == GuardrailAction.ALLOW


def test_blocks_credit_card():
    result = check_user_input("My card is 4111 2222 3333 4444")
    assert result.action == GuardrailAction.BLOCK
    assert "sensitive" in result.replacement_text.lower()


def test_blocks_tfn():
    result = check_user_input("My TFN is 12345678")
    assert result.action == GuardrailAction.BLOCK


def test_warns_on_abuse():
    result = check_user_input("this is bullshit fuck off")
    assert result.action == GuardrailAction.WARN


def test_terminates_on_repeated_abuse():
    result = check_user_input("fuck you", consecutive_off_topic=3)
    assert result.action == GuardrailAction.TERMINATE


def test_warns_off_topic():
    result = check_user_input("what do you think about bitcoin")
    assert result.action == GuardrailAction.WARN


def test_terminates_persistent_off_topic():
    result = check_user_input("tell me about crypto", consecutive_off_topic=3)
    assert result.action == GuardrailAction.TERMINATE


def test_output_allows_normal():
    result = check_agent_output("That suburb has great public transport links.")
    assert result.action == GuardrailAction.ALLOW


def test_output_warns_guarantee():
    result = check_agent_output("I guarantee we will find you the perfect home.")
    assert result.action == GuardrailAction.WARN


def test_call_duration_allows():
    result = check_call_duration(300, 900)
    assert result.action == GuardrailAction.ALLOW


def test_call_duration_warns_near_limit():
    result = check_call_duration(850, 900)
    assert result.action == GuardrailAction.WARN


def test_call_duration_terminates():
    result = check_call_duration(901, 900)
    assert result.action == GuardrailAction.TERMINATE
