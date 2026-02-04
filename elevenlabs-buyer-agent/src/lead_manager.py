"""Lead management for outbound call campaigns.

Handles:
- CSV import of leads
- CRM integration (webhook-based)
- Lead queue management
- Outbound call orchestration via ElevenLabs
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests

from config.settings import Settings


@dataclass
class Lead:
    """A potential buyer lead for outbound calling."""

    name: str
    phone: str
    email: str = ""
    property_address: str = ""
    interest_source: str = ""
    enquiry_date: Optional[datetime] = None
    notes: str = ""
    status: str = "pending"  # pending, called, completed, failed, do_not_call
    interest_level: str = ""  # hot, warm, cool, not_interested
    call_attempts: int = 0
    last_call_date: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def days_since_enquiry(self) -> int:
        """Calculate days since the original enquiry."""
        if not self.enquiry_date:
            return 0
        delta = datetime.now() - self.enquiry_date
        return delta.days

    def to_dynamic_variables(self) -> dict[str, str]:
        """Convert lead to ElevenLabs dynamic variables."""
        return {
            "prospect_name": self.name or "there",
            "property_address": self.property_address or "",
            "interest_source": self.interest_source or "",
            "days_since_enquiry": str(self.days_since_enquiry) if self.enquiry_date else "",
        }


class LeadManager:
    """Manages leads for outbound calling campaigns."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.leads: list[Lead] = []

    def load_from_csv(self, csv_path: str | Path) -> int:
        """Load leads from a CSV file.

        Expected CSV columns:
        - name (required)
        - phone (required)
        - email (optional)
        - property_address (optional)
        - interest_source (optional)
        - enquiry_date (optional, format: YYYY-MM-DD)
        - notes (optional)

        Returns:
            Number of leads loaded
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        loaded = 0
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip rows without required fields
                if not row.get("name") or not row.get("phone"):
                    continue

                # Parse enquiry date if provided
                enquiry_date = None
                if row.get("enquiry_date"):
                    try:
                        enquiry_date = datetime.strptime(row["enquiry_date"], "%Y-%m-%d")
                    except ValueError:
                        pass

                lead = Lead(
                    name=row["name"].strip(),
                    phone=self._normalize_phone(row["phone"]),
                    email=row.get("email", "").strip(),
                    property_address=row.get("property_address", "").strip(),
                    interest_source=row.get("interest_source", "CSV import").strip(),
                    enquiry_date=enquiry_date,
                    notes=row.get("notes", "").strip(),
                )
                self.leads.append(lead)
                loaded += 1

        return loaded

    def add_lead(self, lead: Lead) -> None:
        """Add a single lead to the queue."""
        lead.phone = self._normalize_phone(lead.phone)
        self.leads.append(lead)

    def get_pending_leads(self, max_attempts: int = 3) -> list[Lead]:
        """Get leads that are ready to be called.

        Args:
            max_attempts: Maximum call attempts before skipping a lead

        Returns:
            List of leads ready for calling
        """
        return [
            lead for lead in self.leads
            if lead.status == "pending" and lead.call_attempts < max_attempts
        ]

    def mark_called(self, lead: Lead, outcome: str, interest_level: str = "") -> None:
        """Mark a lead as called with the outcome."""
        lead.status = outcome  # completed, failed, do_not_call
        lead.interest_level = interest_level
        lead.call_attempts += 1
        lead.last_call_date = datetime.now()

    def initiate_outbound_call(
        self,
        lead: Lead,
        agent_id: str,
        from_number: Optional[str] = None,
    ) -> dict[str, Any]:
        """Initiate an outbound call to a lead via ElevenLabs.

        Args:
            lead: The lead to call
            agent_id: ElevenLabs agent ID (buyer brief or sales associate)
            from_number: Optional Twilio number to call from

        Returns:
            API response with call details
        """
        if not self.settings.elevenlabs_api_key:
            raise ValueError("ElevenLabs API key not configured")

        # Build the call request
        call_config = {
            "agent_id": agent_id,
            "to_number": lead.phone,
            "dynamic_variables": lead.to_dynamic_variables(),
        }

        # Add from number if using Twilio
        if from_number or self.settings.twilio_phone_number:
            call_config["from_number"] = from_number or self.settings.twilio_phone_number

        # Make the API call
        response = requests.post(
            "https://api.elevenlabs.io/v1/convai/phone-calls",
            headers={
                "xi-api-key": self.settings.elevenlabs_api_key,
                "Content-Type": "application/json",
            },
            json=call_config,
        )

        if response.status_code != 200:
            lead.status = "failed"
            lead.call_attempts += 1
            raise RuntimeError(f"Failed to initiate call: {response.text}")

        lead.status = "calling"
        lead.call_attempts += 1
        lead.last_call_date = datetime.now()

        return response.json()

    def export_results(self, output_path: str | Path) -> None:
        """Export call results to a CSV file."""
        output_path = Path(output_path)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "name", "phone", "email", "property_address", "interest_source",
                "status", "interest_level", "call_attempts", "last_call_date", "notes"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for lead in self.leads:
                writer.writerow({
                    "name": lead.name,
                    "phone": lead.phone,
                    "email": lead.email,
                    "property_address": lead.property_address,
                    "interest_source": lead.interest_source,
                    "status": lead.status,
                    "interest_level": lead.interest_level,
                    "call_attempts": lead.call_attempts,
                    "last_call_date": lead.last_call_date.isoformat() if lead.last_call_date else "",
                    "notes": lead.notes,
                })

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to E.164 format for Australian numbers."""
        phone = "".join(c for c in phone if c.isdigit() or c == "+")

        # Handle Australian numbers
        if phone.startswith("04"):
            # Mobile: 04XX XXX XXX -> +614XX XXX XXX
            phone = "+61" + phone[1:]
        elif phone.startswith("0"):
            # Landline: 0X XXXX XXXX -> +61X XXXX XXXX
            phone = "+61" + phone[1:]
        elif phone.startswith("614"):
            phone = "+" + phone
        elif not phone.startswith("+"):
            # Assume Australian if no country code
            phone = "+61" + phone

        return phone


class InboundCallRouter:
    """Routes inbound calls to the appropriate agent based on caller ID."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def should_accept_call(self, from_number: str) -> bool:
        """Check if an inbound call should be accepted."""
        return self.settings.is_inbound_allowed(from_number)

    def get_agent_for_call(
        self,
        from_number: str,
        to_number: str,
    ) -> tuple[str, dict[str, str]]:
        """Determine which agent should handle an inbound call.

        Returns:
            Tuple of (agent_id, dynamic_variables)
        """
        # For now, all inbound calls go to the buyer brief agent
        # In the future, could route based on caller ID or IVR selection
        return (
            "",  # Use default agent
            {
                "prospect_name": "there",
                "agency_name": self.settings.agency_name,
            },
        )


def create_sample_csv(output_path: str | Path) -> None:
    """Create a sample CSV file for lead imports."""
    sample_data = [
        {
            "name": "John Smith",
            "phone": "0412345678",
            "email": "john.smith@example.com",
            "property_address": "42 Smith Street, Sydney NSW 2000",
            "interest_source": "Open Home",
            "enquiry_date": "2024-01-15",
            "notes": "Interested in 3-bedroom properties",
        },
        {
            "name": "Sarah Johnson",
            "phone": "0498765432",
            "email": "sarah.j@example.com",
            "property_address": "",
            "interest_source": "Website Enquiry",
            "enquiry_date": "2024-01-20",
            "notes": "First home buyer",
        },
    ]

    output_path = Path(output_path)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["name", "phone", "email", "property_address", "interest_source", "enquiry_date", "notes"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sample_data)
