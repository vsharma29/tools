"""Tool definitions that Claude can call during the interview."""

from __future__ import annotations

SAVE_BUYER_BRIEF_TOOL = {
    "name": "save_buyer_brief",
    "description": (
        "Save the completed buyer brief. Call this once you have gathered enough "
        "information from the prospect and they have confirmed the summary."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "brief_json": {
                "type": "string",
                "description": "The full BuyerBrief as a JSON string.",
            }
        },
        "required": ["brief_json"],
    },
}

TRANSFER_TO_HUMAN_TOOL = {
    "name": "transfer_to_human",
    "description": (
        "Transfer the call to a human buyer's agent. Use when: "
        "the prospect requests it, the conversation goes off-topic, "
        "or the prospect becomes upset."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Why the call is being transferred.",
            }
        },
        "required": ["reason"],
    },
}

SCHEDULE_FOLLOWUP_TOOL = {
    "name": "schedule_followup",
    "description": (
        "Schedule a follow-up call with the prospect when they can't complete "
        "the interview now or want to think about some answers."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "preferred_datetime": {
                "type": "string",
                "description": "Prospect's preferred callback date/time in ISO format.",
            },
            "notes": {
                "type": "string",
                "description": "Context for the follow-up.",
            },
        },
        "required": ["notes"],
    },
}

ALL_TOOLS = [SAVE_BUYER_BRIEF_TOOL, TRANSFER_TO_HUMAN_TOOL, SCHEDULE_FOLLOWUP_TOOL]
