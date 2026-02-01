"""Tests for the buyer brief schema."""

import json

from src.schemas.buyer_brief import (
    BudgetInfo,
    BuyerBrief,
    FinanceStatus,
    InvestmentStrategy,
    PropertyType,
    PurchasePurpose,
)


def test_minimal_brief():
    brief = BuyerBrief(prospect_name="Jane Smith")
    data = json.loads(brief.model_dump_json(exclude_none=True))
    assert data["prospect_name"] == "Jane Smith"
    assert "budget" in data


def test_full_brief():
    brief = BuyerBrief(
        prospect_name="John Doe",
        prospect_phone="+61400000000",
        purchase_purpose=PurchasePurpose.INVESTMENT,
        budget=BudgetInfo(
            min_price=500_000,
            max_price=800_000,
            finance_status=FinanceStatus.PRE_APPROVED,
            first_home_buyer=False,
        ),
        property_requirements__property_types=[PropertyType.HOUSE, PropertyType.TOWNHOUSE],
    )
    # Should serialise without error
    json_str = brief.model_dump_json(exclude_none=True)
    assert "investment" in json_str


def test_investment_criteria():
    brief = BuyerBrief(
        purchase_purpose=PurchasePurpose.INVESTMENT,
    )
    brief.investment_criteria.strategy = InvestmentStrategy.CASH_FLOW
    brief.investment_criteria.target_rental_yield_pct = 5.5
    data = json.loads(brief.model_dump_json(exclude_none=True))
    assert data["investment_criteria"]["strategy"] == "cash_flow"
    assert data["investment_criteria"]["target_rental_yield_pct"] == 5.5
