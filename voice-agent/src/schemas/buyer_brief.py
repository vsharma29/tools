"""Exhaustive Australian residential buyer brief schema.

Covers everything a buyer's agent needs to search, evaluate, and negotiate
on behalf of a residential property buyer in Australia.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PurchasePurpose(str, Enum):
    OWNER_OCCUPIER = "owner_occupier"
    INVESTMENT = "investment"
    DEVELOPMENT = "development"
    SMSF = "smsf"
    HOLIDAY_HOME = "holiday_home"


class InvestmentStrategy(str, Enum):
    CASH_FLOW = "cash_flow"
    CAPITAL_GROWTH = "capital_growth"
    BALANCED = "balanced"
    VALUE_ADD = "value_add"
    SUBDIVISION = "subdivision"


class PropertyType(str, Enum):
    HOUSE = "house"
    TOWNHOUSE = "townhouse"
    VILLA = "villa"
    UNIT_APARTMENT = "unit_apartment"
    DUPLEX = "duplex"
    ACREAGE = "acreage"
    LAND = "land"
    GRANNY_FLAT = "granny_flat"
    OTHER = "other"


class BuyingTimeline(str, Enum):
    IMMEDIATE = "immediate_0_1_month"
    SHORT = "short_1_3_months"
    MEDIUM = "medium_3_6_months"
    LONG = "long_6_12_months"
    EXPLORING = "exploring_12_plus_months"


class FinanceStatus(str, Enum):
    PRE_APPROVED = "pre_approved"
    IN_PROGRESS = "in_progress"
    NOT_STARTED = "not_started"
    CASH_BUYER = "cash_buyer"
    SMSF_FINANCE = "smsf_finance"


class ParkingType(str, Enum):
    GARAGE = "garage"
    CARPORT = "carport"
    OFF_STREET = "off_street"
    ON_STREET = "on_street"
    NONE = "none"


class PoolPreference(str, Enum):
    MUST_HAVE = "must_have"
    NICE_TO_HAVE = "nice_to_have"
    NOT_WANTED = "not_wanted"
    NO_PREFERENCE = "no_preference"


class ConditionPreference(str, Enum):
    MOVE_IN_READY = "move_in_ready"
    MINOR_COSMETIC = "minor_cosmetic"
    MAJOR_RENOVATION = "major_renovation"
    KNOCKDOWN_REBUILD = "knockdown_rebuild"
    NEW_BUILD = "new_build"
    OFF_THE_PLAN = "off_the_plan"
    NO_PREFERENCE = "no_preference"


class AuctionComfort(str, Enum):
    COMFORTABLE = "comfortable"
    PREFER_PRIVATE = "prefer_private_treaty"
    WILL_CONSIDER = "will_consider"
    NO_AUCTIONS = "no_auctions"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class BudgetInfo(BaseModel):
    min_price: Optional[int] = Field(None, description="Minimum purchase price AUD")
    max_price: Optional[int] = Field(None, description="Maximum purchase price AUD")
    stretch_budget: Optional[int] = Field(
        None, description="Absolute ceiling if the right property appears AUD"
    )
    deposit_available: Optional[int] = Field(None, description="Cash deposit available AUD")
    finance_status: Optional[FinanceStatus] = None
    lender_or_broker: Optional[str] = Field(None, description="Current lender or broker name")
    first_home_buyer: Optional[bool] = None
    using_fhog: Optional[bool] = Field(None, description="Using First Home Owner Grant")
    using_fhss: Optional[bool] = Field(None, description="Using First Home Super Saver Scheme")
    stamp_duty_budget_included: Optional[bool] = Field(
        None, description="Does budget include stamp duty and purchase costs"
    )


class LocationPreferences(BaseModel):
    preferred_states: list[str] = Field(default_factory=list, description="e.g. ['NSW','VIC']")
    preferred_cities: list[str] = Field(default_factory=list, description="e.g. ['Sydney','Melbourne']")
    preferred_suburbs: list[str] = Field(default_factory=list)
    preferred_regions: list[str] = Field(
        default_factory=list, description="e.g. ['Inner West','Northern Beaches']"
    )
    excluded_suburbs: list[str] = Field(default_factory=list)
    max_commute_minutes: Optional[int] = Field(None, description="Max commute to work in minutes")
    commute_destination: Optional[str] = Field(None, description="Work address or suburb")
    commute_mode: Optional[str] = Field(None, description="car | public_transport | both")
    proximity_requirements: list[str] = Field(
        default_factory=list,
        description="e.g. ['near beach','close to train station','school catchment XYZ']",
    )
    flood_zone_ok: Optional[bool] = None
    bushfire_zone_ok: Optional[bool] = None


class PropertyRequirements(BaseModel):
    property_types: list[PropertyType] = Field(default_factory=list)
    min_bedrooms: Optional[int] = None
    max_bedrooms: Optional[int] = None
    min_bathrooms: Optional[int] = None
    min_car_spaces: Optional[int] = None
    parking_type: Optional[ParkingType] = None
    min_land_size_sqm: Optional[int] = None
    max_land_size_sqm: Optional[int] = None
    min_internal_size_sqm: Optional[int] = None
    min_frontage_m: Optional[float] = Field(None, description="Minimum lot frontage in metres")
    single_or_double_storey: Optional[str] = Field(None, description="single | double | no_preference")
    pool_preference: Optional[PoolPreference] = None
    outdoor_entertaining: Optional[bool] = None
    granny_flat_or_dual_occ: Optional[bool] = Field(
        None, description="Needs or wants granny flat / dual occupancy potential"
    )
    study_or_home_office: Optional[bool] = None
    separate_living_areas: Optional[int] = Field(None, description="Number of separate living areas")
    air_conditioning: Optional[bool] = None
    solar_panels: Optional[bool] = None
    ev_charging: Optional[bool] = None
    accessibility_needs: Optional[str] = Field(
        None, description="Wheelchair, single level, wide doorways etc."
    )
    pet_friendly: Optional[bool] = None
    north_facing: Optional[bool] = Field(None, description="Preference for north-facing backyard/living")
    view_preference: Optional[str] = Field(None, description="water | city | bush | none")
    condition_preference: Optional[ConditionPreference] = None
    heritage_listing_ok: Optional[bool] = None
    strata_ok: Optional[bool] = Field(None, description="OK with strata / body corporate")
    max_strata_fees_quarterly: Optional[int] = None


class InvestmentCriteria(BaseModel):
    """Only populated when purchase_purpose is investment/smsf/development."""
    strategy: Optional[InvestmentStrategy] = None
    target_rental_yield_pct: Optional[float] = Field(None, description="Minimum gross yield %")
    target_weekly_rent: Optional[int] = None
    depreciation_important: Optional[bool] = None
    negative_gearing_plan: Optional[bool] = None
    existing_portfolio_size: Optional[int] = Field(None, description="Number of existing properties")
    acceptable_vacancy_rate_pct: Optional[float] = None
    subdivision_potential_required: Optional[bool] = None
    development_approval_required: Optional[bool] = None
    tenant_in_place_preferred: Optional[bool] = None
    property_manager_in_place: Optional[bool] = None
    max_annual_holding_cost: Optional[int] = Field(
        None, description="Max annual out-of-pocket after rent AUD"
    )


class LifestyleAndPersonal(BaseModel):
    household_composition: Optional[str] = Field(
        None, description="e.g. couple, family with 2 kids, single, downsizer"
    )
    current_living_situation: Optional[str] = Field(
        None, description="renting | own_and_selling | own_and_keeping | living_with_family"
    )
    school_requirements: list[str] = Field(
        default_factory=list, description="Specific schools or school types (public/private/catholic)"
    )
    childcare_needed: Optional[bool] = None
    lifestyle_priorities: list[str] = Field(
        default_factory=list,
        description="e.g. ['cafe culture','quiet street','close to parks','nightlife']",
    )
    deal_breakers: list[str] = Field(
        default_factory=list,
        description="Absolute non-negotiables e.g. ['no main road','must have garage']",
    )
    nice_to_haves: list[str] = Field(
        default_factory=list,
        description="Preferred but flexible items",
    )


class BuyingProcess(BaseModel):
    timeline: Optional[BuyingTimeline] = None
    auction_comfort: Optional[AuctionComfort] = None
    previous_offers_made: Optional[int] = Field(None, description="Number of offers already made")
    using_buyers_agent_before: Optional[bool] = None
    solicitor_or_conveyancer: Optional[str] = Field(None, description="Name or 'need recommendation'")
    building_and_pest_arranged: Optional[bool] = None
    current_property_to_sell: Optional[bool] = None
    sale_settlement_dependency: Optional[bool] = Field(
        None, description="Is purchase conditional on selling current property"
    )


# ---------------------------------------------------------------------------
# Top-level Buyer Brief
# ---------------------------------------------------------------------------

class BuyerBrief(BaseModel):
    """Complete buyer brief generated from the voice interview."""

    # Meta
    brief_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    agent_notes: Optional[str] = Field(None, description="Free-text notes from the conversation")
    confidence_score: Optional[float] = Field(
        None, ge=0, le=1, description="Agent confidence that brief is complete"
    )

    # Contact
    prospect_name: Optional[str] = None
    prospect_phone: Optional[str] = None
    prospect_email: Optional[str] = None
    preferred_contact_method: Optional[str] = Field(None, description="phone | email | sms | whatsapp")
    best_time_to_call: Optional[str] = None

    # Core sections
    purchase_purpose: Optional[PurchasePurpose] = None
    budget: BudgetInfo = Field(default_factory=BudgetInfo)
    location: LocationPreferences = Field(default_factory=LocationPreferences)
    property_requirements: PropertyRequirements = Field(default_factory=PropertyRequirements)
    investment_criteria: InvestmentCriteria = Field(default_factory=InvestmentCriteria)
    lifestyle: LifestyleAndPersonal = Field(default_factory=LifestyleAndPersonal)
    buying_process: BuyingProcess = Field(default_factory=BuyingProcess)
