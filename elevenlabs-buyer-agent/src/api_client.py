"""ElevenLabs API client for managing agents and phone numbers."""

from __future__ import annotations

import json
from typing import Any, Optional

import httpx

from config.settings import Settings


class ElevenLabsClient:
    """Client for ElevenLabs Conversational AI API."""

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, settings: Settings):
        self._api_key = settings.elevenlabs_api_key
        self._settings = settings
        self._client = httpx.AsyncClient(
            headers={
                "xi-api-key": self._api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "ElevenLabsClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Agent Management
    # ------------------------------------------------------------------

    async def create_agent(self, config: dict[str, Any]) -> dict[str, Any]:
        """Create a new conversational AI agent.

        Args:
            config: Agent configuration dict (see agent_config.py)

        Returns:
            Created agent details including agent_id
        """
        response = await self._client.post(
            f"{self.BASE_URL}/convai/agents/create",
            json=config,
        )
        response.raise_for_status()
        return response.json()

    async def update_agent(self, agent_id: str, config: dict[str, Any]) -> dict[str, Any]:
        """Update an existing agent.

        Args:
            agent_id: The agent's ID
            config: Updated configuration

        Returns:
            Updated agent details
        """
        response = await self._client.patch(
            f"{self.BASE_URL}/convai/agents/{agent_id}",
            json=config,
        )
        response.raise_for_status()
        return response.json()

    async def get_agent(self, agent_id: str) -> dict[str, Any]:
        """Get agent details.

        Args:
            agent_id: The agent's ID

        Returns:
            Agent configuration and status
        """
        response = await self._client.get(
            f"{self.BASE_URL}/convai/agents/{agent_id}",
        )
        response.raise_for_status()
        return response.json()

    async def list_agents(self) -> list[dict[str, Any]]:
        """List all agents in the account.

        Returns:
            List of agent summaries
        """
        response = await self._client.get(f"{self.BASE_URL}/convai/agents")
        response.raise_for_status()
        return response.json().get("agents", [])

    async def delete_agent(self, agent_id: str) -> None:
        """Delete an agent.

        Args:
            agent_id: The agent's ID
        """
        response = await self._client.delete(
            f"{self.BASE_URL}/convai/agents/{agent_id}",
        )
        response.raise_for_status()

    # ------------------------------------------------------------------
    # Phone Numbers (Twilio Integration)
    # ------------------------------------------------------------------

    async def import_twilio_number(
        self,
        agent_id: str,
        phone_number: str,
        label: str = "Buyer Agency Line",
    ) -> dict[str, Any]:
        """Import a Twilio phone number and connect it to an agent.

        Args:
            agent_id: The agent to connect the number to
            phone_number: The Twilio phone number (e.g., +61400000000)
            label: Friendly name for the number

        Returns:
            Phone number registration details
        """
        if not self._settings.has_twilio:
            raise ValueError("Twilio credentials not configured")

        response = await self._client.post(
            f"{self.BASE_URL}/convai/phone-numbers/create",
            json={
                "phone_number": phone_number,
                "label": label,
                "agent_id": agent_id,
                "provider": "twilio",
                "twilio_config": {
                    "account_sid": self._settings.twilio_account_sid,
                    "auth_token": self._settings.twilio_auth_token,
                },
            },
        )
        response.raise_for_status()
        return response.json()

    async def list_phone_numbers(self) -> list[dict[str, Any]]:
        """List all registered phone numbers.

        Returns:
            List of phone number configurations
        """
        response = await self._client.get(f"{self.BASE_URL}/convai/phone-numbers")
        response.raise_for_status()
        return response.json().get("phone_numbers", [])

    async def delete_phone_number(self, phone_number_id: str) -> None:
        """Remove a phone number registration.

        Args:
            phone_number_id: The phone number's ID
        """
        response = await self._client.delete(
            f"{self.BASE_URL}/convai/phone-numbers/{phone_number_id}",
        )
        response.raise_for_status()

    async def initiate_outbound_call(
        self,
        agent_id: str,
        to_number: str,
        from_number_id: str,
        custom_variables: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Initiate an outbound call.

        Args:
            agent_id: The agent to handle the call
            to_number: The number to call
            from_number_id: The registered phone number ID to call from
            custom_variables: Dynamic variables to pass to the agent

        Returns:
            Call initiation details
        """
        payload = {
            "agent_id": agent_id,
            "to_number": to_number,
            "from_number_id": from_number_id,
        }
        if custom_variables:
            payload["custom_llm_extra_body"] = {
                "dynamic_variables": custom_variables
            }

        response = await self._client.post(
            f"{self.BASE_URL}/convai/phone-numbers/outbound-call",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Conversations & Analytics
    # ------------------------------------------------------------------

    async def list_conversations(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List conversations with optional filtering.

        Args:
            agent_id: Filter by agent
            limit: Maximum results to return

        Returns:
            List of conversation summaries
        """
        params = {"limit": limit}
        if agent_id:
            params["agent_id"] = agent_id

        response = await self._client.get(
            f"{self.BASE_URL}/convai/conversations",
            params=params,
        )
        response.raise_for_status()
        return response.json().get("conversations", [])

    async def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        """Get detailed conversation data including transcript and analysis.

        Args:
            conversation_id: The conversation's ID

        Returns:
            Full conversation details
        """
        response = await self._client.get(
            f"{self.BASE_URL}/convai/conversations/{conversation_id}",
        )
        response.raise_for_status()
        return response.json()

    async def get_conversation_audio(self, conversation_id: str) -> bytes:
        """Download conversation audio recording.

        Args:
            conversation_id: The conversation's ID

        Returns:
            Audio bytes (MP3 format)
        """
        response = await self._client.get(
            f"{self.BASE_URL}/convai/conversations/{conversation_id}/audio",
        )
        response.raise_for_status()
        return response.content

    # ------------------------------------------------------------------
    # Agent Testing
    # ------------------------------------------------------------------

    async def run_simulation(
        self,
        agent_id: str,
        scenario: str,
        evaluation_criteria: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Run a conversation simulation for testing.

        Args:
            agent_id: The agent to test
            scenario: Description of the test scenario
            evaluation_criteria: Optional criteria IDs to evaluate

        Returns:
            Simulation results including transcript and evaluations
        """
        payload = {
            "agent_id": agent_id,
            "scenario": scenario,
        }
        if evaluation_criteria:
            payload["evaluation_criteria"] = evaluation_criteria

        response = await self._client.post(
            f"{self.BASE_URL}/convai/simulations/create",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Voices
    # ------------------------------------------------------------------

    async def list_voices(self) -> list[dict[str, Any]]:
        """List available voices.

        Returns:
            List of voice configurations
        """
        response = await self._client.get(f"{self.BASE_URL}/voices")
        response.raise_for_status()
        return response.json().get("voices", [])

    async def get_voice(self, voice_id: str) -> dict[str, Any]:
        """Get voice details.

        Args:
            voice_id: The voice's ID

        Returns:
            Voice configuration and settings
        """
        response = await self._client.get(f"{self.BASE_URL}/voices/{voice_id}")
        response.raise_for_status()
        return response.json()
