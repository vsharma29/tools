"""
Shared Configuration for Voice Agents

Centralizes configuration for:
- ElevenLabs Buyer Agent
- Voice Agent (Claude-based)
- Twilio telephony
- Mem0 memory
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path

# Try to load .env
try:
    from dotenv import load_dotenv
    # Look for .env in multiple locations
    for env_path in ['.env', '../.env', '../../.env']:
        if Path(env_path).exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass


@dataclass
class TwilioConfig:
    """Twilio telephony configuration"""
    account_sid: str = field(default_factory=lambda: os.getenv('TWILIO_ACCOUNT_SID', ''))
    auth_token: str = field(default_factory=lambda: os.getenv('TWILIO_AUTH_TOKEN', ''))
    phone_number: str = field(default_factory=lambda: os.getenv('TWILIO_PHONE_NUMBER', ''))

    @property
    def is_configured(self) -> bool:
        return all([self.account_sid, self.auth_token, self.phone_number])

    def get_api_base_url(self) -> str:
        return f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"


@dataclass
class ElevenLabsConfig:
    """ElevenLabs configuration"""
    api_key: str = field(default_factory=lambda: os.getenv('ELEVENLABS_API_KEY', ''))
    agent_id: str = field(default_factory=lambda: os.getenv('ELEVENLABS_AGENT_ID', ''))
    agent_phone_number: str = field(default_factory=lambda: os.getenv('AGENT_PHONE_NUMBER', ''))

    # Optional: Sales agent
    sales_agent_id: str = field(default_factory=lambda: os.getenv('ELEVENLABS_SALES_AGENT_ID', ''))

    @property
    def is_configured(self) -> bool:
        return all([self.api_key, self.agent_id])

    @property
    def api_base_url(self) -> str:
        return "https://api.elevenlabs.io/v1"


@dataclass
class Mem0Config:
    """Mem0 memory configuration"""
    api_key: str = field(default_factory=lambda: os.getenv('MEM0_API_KEY', ''))
    org_id: str = field(default_factory=lambda: os.getenv('MEM0_ORG_ID', ''))
    project_id: str = field(default_factory=lambda: os.getenv('MEM0_PROJECT_ID', ''))

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def api_base_url(self) -> str:
        return "https://api.mem0.ai/v1"


@dataclass
class VoiceAgentConfig:
    """Claude-based voice agent configuration"""
    anthropic_api_key: str = field(default_factory=lambda: os.getenv('ANTHROPIC_API_KEY', ''))
    deepgram_api_key: str = field(default_factory=lambda: os.getenv('DEEPGRAM_API_KEY', ''))
    cartesia_api_key: str = field(default_factory=lambda: os.getenv('CARTESIA_API_KEY', ''))
    openai_api_key: str = field(default_factory=lambda: os.getenv('OPENAI_API_KEY', ''))

    # Provider selection
    stt_provider: str = field(default_factory=lambda: os.getenv('STT_PROVIDER', 'deepgram'))
    tts_provider: str = field(default_factory=lambda: os.getenv('TTS_PROVIDER', 'cartesia'))

    @property
    def is_configured(self) -> bool:
        return bool(self.anthropic_api_key)


@dataclass
class AgentRegistry:
    """Registry of all agents"""
    agents: dict = field(default_factory=dict)

    def register(self, name: str, agent_type: str, agent_id: str, config: dict = None):
        """Register an agent"""
        self.agents[name] = {
            'type': agent_type,
            'id': agent_id,
            'config': config or {}
        }

    def get(self, name: str) -> Optional[dict]:
        """Get agent by name"""
        return self.agents.get(name)

    def list_agents(self) -> List[str]:
        """List all registered agents"""
        return list(self.agents.keys())


@dataclass
class AppConfig:
    """Main application configuration"""
    twilio: TwilioConfig = field(default_factory=TwilioConfig)
    elevenlabs: ElevenLabsConfig = field(default_factory=ElevenLabsConfig)
    mem0: Mem0Config = field(default_factory=Mem0Config)
    voice_agent: VoiceAgentConfig = field(default_factory=VoiceAgentConfig)
    registry: AgentRegistry = field(default_factory=AgentRegistry)

    # Service URLs
    sms_trigger_url: str = field(default_factory=lambda: os.getenv('SMS_TRIGGER_URL', 'https://smstrigger.vercel.app'))
    memory_service_url: str = field(default_factory=lambda: os.getenv('MEMORY_SERVICE_URL', 'https://memoryservice.vercel.app'))
    web_dashboard_url: str = field(default_factory=lambda: os.getenv('WEB_DASHBOARD_URL', 'https://webdashboard-navy.vercel.app'))

    # Authorization
    authorized_numbers: List[str] = field(default_factory=lambda:
        [n.strip() for n in os.getenv('AUTHORIZED_NUMBERS', '').split(',') if n.strip()]
    )

    def __post_init__(self):
        """Register default agents"""
        if self.elevenlabs.agent_id:
            self.registry.register(
                'buyer-agent',
                'elevenlabs',
                self.elevenlabs.agent_id,
                {'description': 'Buyer interview agent'}
            )

        if self.elevenlabs.sales_agent_id:
            self.registry.register(
                'sales-agent',
                'elevenlabs',
                self.elevenlabs.sales_agent_id,
                {'description': 'Sales associate agent'}
            )

        if self.voice_agent.is_configured:
            self.registry.register(
                'voice-agent',
                'claude',
                'voice-agent-v1',
                {'description': 'Claude-based voice pipeline'}
            )

    def validate(self) -> dict:
        """Validate configuration and return status"""
        return {
            'twilio': {
                'configured': self.twilio.is_configured,
                'phone_number': self.twilio.phone_number if self.twilio.is_configured else None
            },
            'elevenlabs': {
                'configured': self.elevenlabs.is_configured,
                'agent_id': self.elevenlabs.agent_id if self.elevenlabs.is_configured else None,
                'sales_agent_id': self.elevenlabs.sales_agent_id or None
            },
            'mem0': {
                'configured': self.mem0.is_configured
            },
            'voice_agent': {
                'configured': self.voice_agent.is_configured,
                'stt_provider': self.voice_agent.stt_provider,
                'tts_provider': self.voice_agent.tts_provider
            },
            'agents': self.registry.list_agents(),
            'services': {
                'sms_trigger': self.sms_trigger_url,
                'memory': self.memory_service_url,
                'dashboard': self.web_dashboard_url
            }
        }

    def to_env_template(self) -> str:
        """Generate .env template"""
        return """# Twilio Configuration
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

# ElevenLabs Configuration
ELEVENLABS_API_KEY=
ELEVENLABS_AGENT_ID=
ELEVENLABS_SALES_AGENT_ID=
AGENT_PHONE_NUMBER=

# Mem0 Memory
MEM0_API_KEY=
MEM0_ORG_ID=
MEM0_PROJECT_ID=

# Claude Voice Agent (optional)
ANTHROPIC_API_KEY=
DEEPGRAM_API_KEY=
CARTESIA_API_KEY=
OPENAI_API_KEY=
STT_PROVIDER=deepgram
TTS_PROVIDER=cartesia

# Service URLs
SMS_TRIGGER_URL=https://smstrigger.vercel.app
MEMORY_SERVICE_URL=https://memoryservice.vercel.app
WEB_DASHBOARD_URL=https://webdashboard-navy.vercel.app

# Authorization (comma-separated phone numbers)
AUTHORIZED_NUMBERS=
"""


# Global config instance
config = AppConfig()


def get_config() -> AppConfig:
    """Get the global config instance"""
    return config


def reload_config() -> AppConfig:
    """Reload configuration from environment"""
    global config
    config = AppConfig()
    return config
