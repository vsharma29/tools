"""
Shared Memory Module for Voice Agents

Provides Mem0 integration for both ElevenLabs and Claude-based agents.
Uses phone number as unique identifier for persistent memory.
"""

import os
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime


class MemoryClient:
    """
    Unified memory client for voice agents.
    Uses Mem0 for persistent storage with phone number as user ID.
    """

    def __init__(
        self,
        api_key: str = None,
        org_id: str = None,
        project_id: str = None,
        base_url: str = "https://api.mem0.ai/v1"
    ):
        self.api_key = api_key or os.getenv('MEM0_API_KEY', '')
        self.org_id = org_id or os.getenv('MEM0_ORG_ID', '')
        self.project_id = project_id or os.getenv('MEM0_PROJECT_ID', '')
        self.base_url = base_url

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to use as user_id"""
        return ''.join(c for c in phone if c.isdigit() or c == '+')

    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make authenticated request to Mem0 API"""
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }

        url = f"{self.base_url}{endpoint}"

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=data, timeout=10)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=10)
            else:
                return {'success': False, 'error': f'Unsupported method: {method}'}

            if response.status_code in [200, 201]:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': f'API error: {response.status_code}'}

        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': str(e)}

    def add_memory(
        self,
        phone: str,
        message: str,
        metadata: dict = None
    ) -> dict:
        """
        Add a memory for a phone number.

        Args:
            phone: Phone number as unique identifier
            message: The information to remember
            metadata: Optional metadata (call_id, agent, timestamp)

        Returns:
            dict with success status
        """
        if not self.is_configured:
            return {'success': False, 'error': 'Mem0 not configured'}

        user_id = self._normalize_phone(phone)

        payload = {
            "messages": [{"role": "user", "content": message}],
            "user_id": user_id,
            "metadata": metadata or {}
        }

        if self.org_id:
            payload["org_id"] = self.org_id
        if self.project_id:
            payload["project_id"] = self.project_id

        return self._request('POST', '/memories/', payload)

    def search_memories(
        self,
        phone: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search memories for a phone number.

        Args:
            phone: Phone number as unique identifier
            query: Search query for semantic matching
            limit: Max results to return

        Returns:
            List of matching memories
        """
        if not self.is_configured:
            return []

        user_id = self._normalize_phone(phone)

        payload = {
            "query": query,
            "user_id": user_id,
            "limit": limit
        }

        if self.org_id:
            payload["org_id"] = self.org_id
        if self.project_id:
            payload["project_id"] = self.project_id

        result = self._request('POST', '/memories/search/', payload)

        if result['success']:
            return result['data'].get('results', [])
        return []

    def get_all_memories(self, phone: str) -> List[Dict[str, Any]]:
        """Get all memories for a phone number"""
        if not self.is_configured:
            return []

        user_id = self._normalize_phone(phone)

        params = {"user_id": user_id}
        if self.org_id:
            params["org_id"] = self.org_id
        if self.project_id:
            params["project_id"] = self.project_id

        result = self._request('GET', '/memories/', params)

        if result['success']:
            data = result['data']
            return data.get('results', data) if isinstance(data, dict) else data
        return []

    def get_context_for_call(self, phone: str) -> str:
        """
        Get formatted context for a phone call.
        Use at the start of each call.

        Args:
            phone: Caller's phone number

        Returns:
            Formatted string with caller history
        """
        memories = self.search_memories(
            phone,
            "previous interactions preferences interests requirements",
            limit=5
        )

        if not memories:
            return ""

        memory_texts = [m.get('memory', '') for m in memories if m.get('memory')]

        if memory_texts:
            return f"CALLER HISTORY ({phone}):\n" + "\n".join(f"- {m}" for m in memory_texts)

        return ""

    def save_call_summary(
        self,
        phone: str,
        summary: str,
        agent_name: str = "voice-agent",
        call_id: str = None
    ) -> dict:
        """
        Save a call summary.
        Use at the end of each call.

        Args:
            phone: Caller's phone number
            summary: Summary of the conversation
            agent_name: Name of the agent
            call_id: Optional call identifier

        Returns:
            dict with success status
        """
        return self.add_memory(
            phone,
            f"Call summary: {summary}",
            {
                "type": "call_summary",
                "agent": agent_name,
                "call_id": call_id,
                "timestamp": datetime.now().isoformat()
            }
        )


# Claude-specific memory tools for voice-agent integration
def create_memory_tools(memory_client: MemoryClient, phone: str):
    """
    Create memory tool functions for Claude agent.

    Args:
        memory_client: Configured MemoryClient
        phone: Current caller's phone number

    Returns:
        Dict of tool functions to register with Claude
    """

    async def retrieve_memories(query: str) -> str:
        """Retrieve relevant memories for this caller"""
        memories = memory_client.search_memories(phone, query, limit=5)

        if not memories:
            return "No previous interactions found for this caller."

        memory_texts = [m.get('memory', '') for m in memories if m.get('memory')]
        if memory_texts:
            return "Previous interactions:\n" + "\n".join(f"- {m}" for m in memory_texts)

        return "No specific memories found for this query."

    async def add_memories(message: str) -> str:
        """Store important information for future calls"""
        result = memory_client.add_memory(phone, message)
        if result['success']:
            return "Information saved for future reference."
        return "Could not save memory at this time."

    return {
        'retrieve_memories': retrieve_memories,
        'add_memories': add_memories
    }


# Singleton instance
_memory_client = None


def get_memory_client() -> MemoryClient:
    """Get or create the global memory client"""
    global _memory_client
    if _memory_client is None:
        _memory_client = MemoryClient()
    return _memory_client
