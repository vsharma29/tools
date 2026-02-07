#!/usr/bin/env python3
"""
Unified Agent Manager

CLI tool to manage all voice agents:
- ElevenLabs agents (buyer, sales)
- Claude-based voice agent
- Twilio configuration
- Memory service
"""

import os
import sys
import argparse
import json
import requests
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from shared.config import get_config, AppConfig
    from shared.memory import get_memory_client, MemoryClient
except ImportError:
    # Fallback for direct execution
    from config import get_config, AppConfig
    from memory import get_memory_client, MemoryClient


class AgentManager:
    """Unified manager for all voice agents"""

    def __init__(self, config: AppConfig = None):
        self.config = config or get_config()
        self.memory = get_memory_client()

    # ==========================================
    # STATUS & CONFIGURATION
    # ==========================================

    def status(self) -> dict:
        """Get status of all configured services"""
        status = self.config.validate()

        # Test service endpoints
        services_status = {}
        for name, url in [
            ('sms_trigger', self.config.sms_trigger_url),
            ('memory', self.config.memory_service_url),
            ('dashboard', self.config.web_dashboard_url)
        ]:
            try:
                resp = requests.get(f"{url}/health", timeout=5)
                services_status[name] = {
                    'url': url,
                    'status': 'online' if resp.status_code == 200 else 'error',
                    'code': resp.status_code
                }
            except:
                services_status[name] = {
                    'url': url,
                    'status': 'offline'
                }

        status['services_health'] = services_status
        return status

    def list_agents(self) -> list:
        """List all registered agents"""
        agents = []
        for name in self.config.registry.list_agents():
            agent = self.config.registry.get(name)
            agents.append({
                'name': name,
                'type': agent['type'],
                'id': agent['id'],
                'description': agent['config'].get('description', '')
            })
        return agents

    # ==========================================
    # TWILIO OPERATIONS
    # ==========================================

    def twilio_status(self) -> dict:
        """Get Twilio phone number configuration"""
        if not self.config.twilio.is_configured:
            return {'error': 'Twilio not configured'}

        url = f"{self.config.twilio.get_api_base_url()}/IncomingPhoneNumbers.json"
        auth = (self.config.twilio.account_sid, self.config.twilio.auth_token)

        try:
            resp = requests.get(url, auth=auth, timeout=10)
            data = resp.json()

            numbers = []
            for num in data.get('incoming_phone_numbers', []):
                numbers.append({
                    'phone': num.get('phone_number'),
                    'friendly_name': num.get('friendly_name'),
                    'voice_url': num.get('voice_url'),
                    'sms_url': num.get('sms_url'),
                    'capabilities': num.get('capabilities')
                })

            return {'numbers': numbers}
        except Exception as e:
            return {'error': str(e)}

    def twilio_call_logs(self, limit: int = 10) -> list:
        """Get recent Twilio call logs"""
        if not self.config.twilio.is_configured:
            return []

        url = f"{self.config.twilio.get_api_base_url()}/Calls.json?PageSize={limit}"
        auth = (self.config.twilio.account_sid, self.config.twilio.auth_token)

        try:
            resp = requests.get(url, auth=auth, timeout=10)
            data = resp.json()

            calls = []
            for call in data.get('calls', []):
                calls.append({
                    'sid': call.get('sid'),
                    'from': call.get('from_formatted'),
                    'to': call.get('to_formatted'),
                    'status': call.get('status'),
                    'direction': call.get('direction'),
                    'duration': call.get('duration'),
                    'date': call.get('date_created')
                })

            return calls
        except Exception as e:
            return []

    def twilio_update_webhooks(
        self,
        phone_sid: str,
        voice_url: str = None,
        sms_url: str = None
    ) -> dict:
        """Update Twilio phone number webhooks"""
        if not self.config.twilio.is_configured:
            return {'error': 'Twilio not configured'}

        url = f"{self.config.twilio.get_api_base_url()}/IncomingPhoneNumbers/{phone_sid}.json"
        auth = (self.config.twilio.account_sid, self.config.twilio.auth_token)

        data = {}
        if voice_url:
            data['VoiceUrl'] = voice_url
            data['VoiceMethod'] = 'POST'
        if sms_url:
            data['SmsUrl'] = sms_url
            data['SmsMethod'] = 'POST'

        try:
            resp = requests.post(url, auth=auth, data=data, timeout=10)
            return resp.json()
        except Exception as e:
            return {'error': str(e)}

    # ==========================================
    # ELEVENLABS OPERATIONS
    # ==========================================

    def elevenlabs_initiate_call(
        self,
        agent_name: str,
        phone: str,
        name: str = "Unknown",
        context: str = ""
    ) -> dict:
        """Initiate an outbound call via ElevenLabs"""
        agent = self.config.registry.get(agent_name)
        if not agent or agent['type'] != 'elevenlabs':
            return {'error': f'ElevenLabs agent not found: {agent_name}'}

        if not self.config.elevenlabs.is_configured:
            return {'error': 'ElevenLabs not configured'}

        # Get caller memory context
        memory_context = ""
        if self.memory.is_configured:
            memory_context = self.memory.get_context_for_call(phone)

        # Combine context
        full_context = context
        if memory_context:
            full_context = f"{memory_context}\n\n{context}" if context else memory_context

        url = "https://api.elevenlabs.io/v1/convai/conversations/call"
        headers = {
            "xi-api-key": self.config.elevenlabs.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "agent_id": agent['id'],
            "agent_phone_number": self.config.elevenlabs.agent_phone_number,
            "customer_phone_number": phone,
            "conversation_initiation_client_data": {
                "dynamic_variables": {
                    "prospect_name": name,
                    "context": full_context
                }
            }
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                return {
                    'success': True,
                    'conversation_id': data.get('conversation_id'),
                    'call_sid': data.get('call_sid')
                }
            else:
                return {
                    'success': False,
                    'error': f'API error {resp.status_code}: {resp.text}'
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ==========================================
    # MEMORY OPERATIONS
    # ==========================================

    def memory_get(self, phone: str) -> list:
        """Get all memories for a phone number"""
        return self.memory.get_all_memories(phone)

    def memory_search(self, phone: str, query: str) -> list:
        """Search memories for a phone number"""
        return self.memory.search_memories(phone, query)

    def memory_add(self, phone: str, message: str, agent: str = "manual") -> dict:
        """Add a memory for a phone number"""
        return self.memory.add_memory(phone, message, {"agent": agent})

    # ==========================================
    # BATCH OPERATIONS
    # ==========================================

    def campaign_start(
        self,
        agent_name: str,
        prospects: list,
        delay_seconds: int = 60
    ) -> dict:
        """
        Start a calling campaign.

        Args:
            agent_name: Name of the agent to use
            prospects: List of dicts with 'phone', 'name', 'context'
            delay_seconds: Delay between calls

        Returns:
            Campaign status
        """
        import time

        results = []
        for i, prospect in enumerate(prospects):
            print(f"Calling {i+1}/{len(prospects)}: {prospect.get('name', 'Unknown')}")

            result = self.elevenlabs_initiate_call(
                agent_name,
                prospect['phone'],
                prospect.get('name', 'Unknown'),
                prospect.get('context', '')
            )

            results.append({
                'prospect': prospect,
                'result': result
            })

            if i < len(prospects) - 1:
                print(f"Waiting {delay_seconds}s before next call...")
                time.sleep(delay_seconds)

        success = sum(1 for r in results if r['result'].get('success'))
        return {
            'total': len(prospects),
            'success': success,
            'failed': len(prospects) - success,
            'results': results
        }


# ==========================================
# CLI INTERFACE
# ==========================================

def print_json(data):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description='Unified Voice Agent Manager')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Status command
    subparsers.add_parser('status', help='Show status of all services')

    # Agents command
    subparsers.add_parser('agents', help='List all registered agents')

    # Twilio commands
    twilio_parser = subparsers.add_parser('twilio', help='Twilio operations')
    twilio_sub = twilio_parser.add_subparsers(dest='twilio_cmd')
    twilio_sub.add_parser('status', help='Show Twilio configuration')
    twilio_sub.add_parser('calls', help='Show recent calls')

    # Call command
    call_parser = subparsers.add_parser('call', help='Initiate an outbound call')
    call_parser.add_argument('agent', help='Agent name (buyer-agent, sales-agent)')
    call_parser.add_argument('phone', help='Phone number to call')
    call_parser.add_argument('--name', default='Unknown', help='Prospect name')
    call_parser.add_argument('--context', default='', help='Call context')

    # Memory commands
    memory_parser = subparsers.add_parser('memory', help='Memory operations')
    memory_sub = memory_parser.add_subparsers(dest='memory_cmd')

    mem_get = memory_sub.add_parser('get', help='Get memories for phone')
    mem_get.add_argument('phone', help='Phone number')

    mem_search = memory_sub.add_parser('search', help='Search memories')
    mem_search.add_argument('phone', help='Phone number')
    mem_search.add_argument('query', help='Search query')

    mem_add = memory_sub.add_parser('add', help='Add memory')
    mem_add.add_argument('phone', help='Phone number')
    mem_add.add_argument('message', help='Message to remember')

    args = parser.parse_args()

    manager = AgentManager()

    if args.command == 'status':
        print_json(manager.status())

    elif args.command == 'agents':
        print_json(manager.list_agents())

    elif args.command == 'twilio':
        if args.twilio_cmd == 'status':
            print_json(manager.twilio_status())
        elif args.twilio_cmd == 'calls':
            print_json(manager.twilio_call_logs())
        else:
            print("Usage: agent_manager.py twilio [status|calls]")

    elif args.command == 'call':
        result = manager.elevenlabs_initiate_call(
            args.agent,
            args.phone,
            args.name,
            args.context
        )
        print_json(result)

    elif args.command == 'memory':
        if args.memory_cmd == 'get':
            print_json(manager.memory_get(args.phone))
        elif args.memory_cmd == 'search':
            print_json(manager.memory_search(args.phone, args.query))
        elif args.memory_cmd == 'add':
            print_json(manager.memory_add(args.phone, args.message))
        else:
            print("Usage: agent_manager.py memory [get|search|add] ...")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
