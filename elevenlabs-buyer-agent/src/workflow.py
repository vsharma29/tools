"""Workflow configuration with subagents for structured buyer brief interviews.

ElevenLabs Workflows allow complex conversation flows with specialized subagents.
This workflow routes prospects through interview stages:

1. Greeting → Qualification
2. Budget & Finance
3. Location Preferences
4. Property Requirements
5. Investment Criteria (conditional)
6. Lifestyle & Personal
7. Buying Process
8. Summary & Confirmation
9. Save Brief & Wrap-up

Each stage uses a focused subagent with scoped prompts and tools.
"""

from __future__ import annotations

from typing import Any

from config.settings import Settings


def build_workflow_config(settings: Settings) -> dict[str, Any]:
    """Build the workflow configuration with subagents for structured interviews.

    This creates a visual flow graph with specialized subagents for each
    interview section, allowing better context scoping and response quality.

    Args:
        settings: Application settings

    Returns:
        Workflow configuration dict for ElevenLabs API
    """
    return {
        "name": "Buyer Brief Interview Workflow",
        "description": "Structured interview flow for Australian residential buyer briefs",
        "nodes": _build_workflow_nodes(settings),
        "edges": _build_workflow_edges(),
        "initial_node": "greeting",
    }


def _build_workflow_nodes(settings: Settings) -> list[dict[str, Any]]:
    """Build all workflow nodes including subagents."""
    nodes = []

    # Node 1: Greeting & Qualification
    nodes.append({
        "id": "greeting",
        "type": "subagent",
        "subagent": {
            "name": "Greeting Agent",
            "prompt": f"""\
You are Ava from {settings.agency_name}. Your role is to warmly greet the caller, \
confirm their name, and briefly explain the purpose of the call.

Your goals:
1. Greet the caller warmly and naturally
2. Confirm their name
3. Explain you'll be gathering information to understand their property needs
4. Ask if now is a good time to chat

Keep it brief — this is just the introduction. After confirmation, the conversation \
will naturally flow to understanding their property needs.

If they seem rushed or unavailable, offer to schedule a callback.
""",
            "llm": settings.elevenlabs_llm_model,
            "temperature": 0.4,
        },
        "transition_prompt": (
            "If the caller is ready to proceed, route to budget_finance. "
            "If they want to reschedule, route to reschedule. "
            "If they seem unqualified or not interested, route to end_call."
        ),
    })

    # Node 2: Budget & Finance
    nodes.append({
        "id": "budget_finance",
        "type": "subagent",
        "subagent": {
            "name": "Budget & Finance Agent",
            "prompt": """\
You are gathering budget and finance information for a buyer brief. \
Focus on understanding their financial position.

Cover these topics:
- Price range (minimum and maximum they're comfortable with)
- Stretch budget (absolute ceiling if the perfect property appears)
- Deposit available
- Finance status (pre-approved, in progress, not started, cash buyer)
- If first home buyer: FHOG, FHSS eligibility
- Whether their budget includes stamp duty and purchase costs

Be conversational, not interrogative. It's okay if they don't know exact figures — \
get approximate ranges. Don't give financial advice.

Once you have a reasonable picture of their budget, naturally transition to location.
""",
            "llm": settings.elevenlabs_llm_model,
            "temperature": 0.3,
        },
        "transition_prompt": (
            "When budget information is sufficiently gathered, route to location_preferences."
        ),
    })

    # Node 3: Location Preferences
    nodes.append({
        "id": "location_preferences",
        "type": "subagent",
        "subagent": {
            "name": "Location Preferences Agent",
            "prompt": """\
You are gathering location preferences for a buyer brief. \
Focus on understanding where they want to live or invest.

Cover these topics:
- Preferred states, cities, suburbs, or regions
- Any areas they want to exclude (and why)
- Commute requirements (work location, max time, car vs public transport)
- Proximity needs (beach, train station, specific schools, hospitals)
- Flood zone or bushfire zone tolerance

Use Australian terminology (suburb not neighborhood). If they mention a broad area, \
ask if there are specific suburbs within that area they prefer.

Once you have a clear picture of their location preferences, transition to property type.
""",
            "llm": settings.elevenlabs_llm_model,
            "temperature": 0.3,
        },
        "transition_prompt": (
            "When location preferences are clear, route to property_requirements."
        ),
    })

    # Node 4: Property Requirements
    nodes.append({
        "id": "property_requirements",
        "type": "subagent",
        "subagent": {
            "name": "Property Requirements Agent",
            "prompt": """\
You are gathering property requirements for a buyer brief. \
Focus on understanding what type of property they need.

Cover these topics:
- Property type (house, townhouse, unit/apartment, villa, duplex, acreage, land)
- Bedrooms and bathrooms needed
- Car spaces and parking type
- Land size requirements (if applicable)
- Internal size requirements
- Key features: pool, outdoor entertaining, study/home office, granny flat potential
- Condition: move-in ready, cosmetic renovation, major renovation, knockdown rebuild
- Strata/body corporate tolerance and maximum fees
- Any accessibility requirements
- Pet-friendly needs
- Preferences: north-facing, views, single/double storey

Don't rush through all items — focus on what matters most to them. \
Some items won't be relevant to every buyer.

Based on their purchase purpose, decide whether to ask about investment criteria.
""",
            "llm": settings.elevenlabs_llm_model,
            "temperature": 0.3,
        },
        "transition_prompt": (
            "If the buyer mentioned investment, SMSF, or development, route to investment_criteria. "
            "Otherwise, route to lifestyle_personal."
        ),
    })

    # Node 5: Investment Criteria (conditional)
    nodes.append({
        "id": "investment_criteria",
        "type": "subagent",
        "subagent": {
            "name": "Investment Criteria Agent",
            "prompt": """\
You are gathering investment criteria for a buyer brief. \
This buyer is purchasing for investment purposes.

Cover these topics:
- Investment strategy: cash flow focus, capital growth focus, or balanced
- Target rental yield percentage
- Target weekly rent
- Importance of depreciation benefits
- Negative gearing plans
- Size of existing property portfolio
- Acceptable vacancy rate
- Subdivision or development potential requirements
- Preference for tenant already in place
- Maximum annual out-of-pocket cost (after rent)

Be conversational. Many investors may not know all these details — \
guide them and explain concepts briefly if needed. Don't give investment advice.

After gathering investment criteria, transition to lifestyle considerations.
""",
            "llm": settings.elevenlabs_llm_model,
            "temperature": 0.3,
        },
        "transition_prompt": "When investment criteria are gathered, route to lifestyle_personal.",
    })

    # Node 6: Lifestyle & Personal
    nodes.append({
        "id": "lifestyle_personal",
        "type": "subagent",
        "subagent": {
            "name": "Lifestyle & Personal Agent",
            "prompt": """\
You are gathering lifestyle and personal information for a buyer brief. \
This helps match properties to the buyer's life situation.

Cover these topics:
- Household composition (single, couple, family with kids, downsizers)
- Current living situation (renting, own and selling, living with family)
- School requirements (specific schools or types: public, private, catholic)
- Childcare needs
- Lifestyle priorities (cafe culture, quiet street, parks, nightlife, community)
- Absolute deal-breakers (things that would rule out a property)
- Nice-to-haves (preferred but flexible)

This is a more personal section — be warm and conversational. \
People often have strong feelings about these topics.

After understanding their lifestyle needs, move to the buying process.
""",
            "llm": settings.elevenlabs_llm_model,
            "temperature": 0.4,
        },
        "transition_prompt": "When lifestyle information is gathered, route to buying_process.",
    })

    # Node 7: Buying Process
    nodes.append({
        "id": "buying_process",
        "type": "subagent",
        "subagent": {
            "name": "Buying Process Agent",
            "prompt": """\
You are gathering information about the buyer's purchase timeline and process.

Cover these topics:
- Timeline: when do they want to buy? (immediately, 1-3 months, 3-6 months, longer)
- Auction comfort level (comfortable, prefer private treaty, will consider, no auctions)
- Number of offers already made (if any)
- Have they used a buyer's agent before?
- Do they have a solicitor/conveyancer? (or need a recommendation)
- Building and pest inspection — have they thought about this?
- Do they have a current property to sell?
- Is the purchase conditional on selling their current property?

This helps understand their readiness and any dependencies.

After gathering process information, move to summary and confirmation.
""",
            "llm": settings.elevenlabs_llm_model,
            "temperature": 0.3,
        },
        "transition_prompt": "When process information is gathered, route to summary_confirmation.",
    })

    # Node 8: Summary & Confirmation
    nodes.append({
        "id": "summary_confirmation",
        "type": "subagent",
        "subagent": {
            "name": "Summary & Confirmation Agent",
            "prompt": """\
You are summarising the buyer brief and confirming it with the prospect.

Your tasks:
1. Provide a concise summary of the key points gathered:
   - Budget range and finance status
   - Preferred locations
   - Property type and key requirements
   - Timeline and readiness

2. Ask if the summary sounds accurate
3. Ask if there's anything important that was missed
4. Make any corrections or additions they mention

Keep the summary conversational — don't just read a list. \
Highlight the most important aspects.

Once they confirm the summary is accurate, proceed to save the brief.
""",
            "llm": settings.elevenlabs_llm_model,
            "temperature": 0.4,
        },
        "transition_prompt": "When the prospect confirms the summary, route to save_brief.",
    })

    # Node 9: Save Brief (tool node)
    nodes.append({
        "id": "save_brief",
        "type": "tool",
        "tool_name": "save_buyer_brief",
        "tool_description": "Save the complete buyer brief to the CRM",
        "success_path": "wrap_up",
        "failure_path": "wrap_up",  # Still wrap up gracefully on failure
    })

    # Node 10: Wrap-up
    nodes.append({
        "id": "wrap_up",
        "type": "subagent",
        "subagent": {
            "name": "Wrap-up Agent",
            "prompt": f"""\
You are wrapping up the buyer brief interview.

Your tasks:
1. Thank the prospect for their time
2. Explain next steps:
   - One of our buyer's agents will review the brief
   - They'll be in touch within [timeframe based on urgency]
   - The agent will discuss strategy and next steps
3. Confirm the best way to reach them
4. Wish them well and end the call positively

Keep it warm and professional. This is the last impression they'll have of {settings.agency_name}.
""",
            "llm": settings.elevenlabs_llm_model,
            "temperature": 0.4,
        },
        "transition_prompt": "After thanking them, route to end_call.",
    })

    # Node 11: End Call
    nodes.append({
        "id": "end_call",
        "type": "system",
        "system_action": "end_call",
    })

    # Node 12: Reschedule (alternative path)
    nodes.append({
        "id": "reschedule",
        "type": "subagent",
        "subagent": {
            "name": "Reschedule Agent",
            "prompt": """\
The prospect isn't available to chat now. Your goal is to schedule a callback.

Ask:
1. When would be a better time to call?
2. Confirm their phone number is correct
3. Any preference for morning/afternoon/evening?

Be understanding and flexible. After scheduling, end the call politely.
""",
            "llm": settings.elevenlabs_llm_model,
            "temperature": 0.4,
        },
        "transition_prompt": "After scheduling the callback, route to end_call.",
    })

    return nodes


def _build_workflow_edges() -> list[dict[str, Any]]:
    """Build the edges connecting workflow nodes."""
    return [
        # Main flow
        {"from": "greeting", "to": "budget_finance", "condition": "proceed"},
        {"from": "greeting", "to": "reschedule", "condition": "reschedule"},
        {"from": "greeting", "to": "end_call", "condition": "not_interested"},

        {"from": "budget_finance", "to": "location_preferences"},
        {"from": "location_preferences", "to": "property_requirements"},

        # Conditional investment branch
        {"from": "property_requirements", "to": "investment_criteria", "condition": "is_investor"},
        {"from": "property_requirements", "to": "lifestyle_personal", "condition": "not_investor"},

        {"from": "investment_criteria", "to": "lifestyle_personal"},
        {"from": "lifestyle_personal", "to": "buying_process"},
        {"from": "buying_process", "to": "summary_confirmation"},
        {"from": "summary_confirmation", "to": "save_brief"},

        # Tool node paths
        {"from": "save_brief", "to": "wrap_up", "condition": "success"},
        {"from": "save_brief", "to": "wrap_up", "condition": "failure"},

        {"from": "wrap_up", "to": "end_call"},
        {"from": "reschedule", "to": "end_call"},
    ]


def build_simple_agent_config(settings: Settings) -> dict[str, Any]:
    """Build a simpler single-agent configuration without workflows.

    Use this if you want the simpler approach without subagent routing.
    The main agent handles the entire interview flow.

    Args:
        settings: Application settings

    Returns:
        Agent configuration without workflows
    """
    from .agent_config import build_agent_config
    return build_agent_config(settings)
