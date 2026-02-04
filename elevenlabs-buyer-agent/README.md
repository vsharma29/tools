# ElevenLabs Buyer Voice Agent

Australian residential buyer agency voice agent built on the **ElevenLabs Conversational AI platform**. Conducts phone interviews with prospects to generate comprehensive buyer briefs.

## Why ElevenLabs Platform?

| Feature | Benefit |
|---------|---------|
| **Managed infrastructure** | No STT/TTS/LLM orchestration code needed |
| **Built-in Twilio integration** | Native phone number import, outbound calls |
| **Low latency** | Optimised voice pipeline with speculative turn-taking |
| **Evaluations & analytics** | Automatic conversation scoring and data extraction |
| **Visual workflows** | Build complex interview flows with subagents |
| **Voice cloning** | Use custom voices for brand consistency |

## Architecture

```
┌─────────────┐     ┌──────────────────────┐     ┌─────────────┐
│  Phone Call  │◄───►│  ElevenLabs Platform  │◄───►│  Webhooks   │
│  (Twilio)    │     │                      │     │  (Your CRM) │
└─────────────┘     │  ┌────────────────┐  │     └─────────────┘
                    │  │ Buyer Brief    │  │
                    │  │ Agent (Claude) │  │     ┌─────────────┐
                    │  └────────────────┘  │◄───►│  S3 Storage │
                    │  ┌────────────────┐  │     └─────────────┘
                    │  │ Voice (Custom) │  │
                    │  └────────────────┘  │
                    │  ┌────────────────┐  │
                    │  │ Evaluations    │  │
                    │  └────────────────┘  │
                    └──────────────────────┘
```

## Quick Start

### 1. Install

```bash
cd elevenlabs-buyer-agent
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your API keys
```

**Required:**
```bash
ELEVENLABS_API_KEY=xi_...  # Get from elevenlabs.io/app/settings/api-keys
```

**Optional (for phone calls):**
```bash
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+61...
```

### 3. Deploy Agent

```bash
# Deploy single-agent mode (simpler)
buyer-agent deploy

# Or deploy with workflow (subagents for each interview section)
buyer-agent deploy --workflow
```

Save the Agent ID that's returned.

### 4. Test via Dashboard

1. Go to [elevenlabs.io/app/agents](https://elevenlabs.io/app/agents)
2. Find your agent
3. Click "Test" to have a conversation via browser

### 5. Connect Phone Number (optional)

```bash
# Import your Twilio number
buyer-agent twilio-setup <agent_id> --label "Buyer Agency Line"

# Make an outbound call
buyer-agent call <agent_id> +61400000000 <phone_number_id> --name "Jane Smith"
```

## CLI Commands

```bash
# Deployment
buyer-agent deploy              # Create new agent
buyer-agent deploy --workflow   # Create with subagent workflow
buyer-agent deploy -u <id>      # Update existing agent
buyer-agent list-agents         # List all agents
buyer-agent delete-agent <id>   # Delete an agent

# Twilio
buyer-agent twilio-setup <agent_id>   # Import Twilio number
buyer-agent list-numbers              # List registered numbers
buyer-agent call <agent_id> <to> <from_id>  # Make outbound call

# Conversations
buyer-agent list-calls              # List recent conversations
buyer-agent get-call <id>           # Get conversation details
buyer-agent get-call <id> -t        # Include transcript

# Testing
buyer-agent test <agent_id>         # Run simulation
buyer-agent test <agent_id> -s "Custom scenario description"

# Utilities
buyer-agent voices                  # List available voices
buyer-agent show-config             # Show current configuration
```

## Configuration Reference

### Voice Settings

```bash
# Use a specific voice (find IDs with `buyer-agent voices`)
ELEVENLABS_VOICE_ID=cjVigY5qzO86Huf0OWal

# TTS model (eleven_turbo_v2_5 for speed, eleven_multilingual_v2 for quality)
ELEVENLABS_TTS_MODEL=eleven_turbo_v2_5

# Voice parameters (0-1)
ELEVENLABS_VOICE_STABILITY=0.5
ELEVENLABS_SIMILARITY_BOOST=0.75
ELEVENLABS_SPEECH_SPEED=1.0
```

### LLM Settings

```bash
# Model options: claude-3-5-sonnet, gpt-4o, gemini-2.0-flash
ELEVENLABS_LLM_MODEL=claude-3-5-sonnet

# Temperature (0-1, lower = more consistent)
ELEVENLABS_LLM_TEMPERATURE=0.3
```

### Webhook Configuration

```bash
# URL to receive completed buyer briefs
WEBHOOK_URL=https://your-crm.example.com/api/briefs

# Secret for verifying webhook authenticity
WEBHOOK_SECRET=your-secret-key
```

## Workflow Mode

The `--workflow` flag deploys the agent with specialised subagents for each interview section:

```
Greeting → Budget & Finance → Location → Property Requirements
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
            (if investor)              (if owner-occupier)            │
                    ▼                        ▼                        │
          Investment Criteria        Lifestyle & Personal ◄───────────┘
                    │                        │
                    └────────────────────────┼────────────────────────┐
                                             ▼                        │
                                      Buying Process                  │
                                             │                        │
                                             ▼                        │
                                    Summary & Confirmation            │
                                             │                        │
                                             ▼                        │
                                      Save Brief → Wrap-up → End Call
```

**Benefits:**
- Each subagent has focused context → better responses
- Conditional routing (investment criteria only for investors)
- Easier to debug and improve individual sections

## Evaluations

The agent is configured with automatic success evaluations:

| Criterion | Description |
|-----------|-------------|
| `brief_completeness` | Were budget, location, property, and timeline covered? |
| `customer_satisfaction` | Did the conversation end positively? |
| `stayed_on_topic` | Did agent avoid giving advice outside scope? |
| `brief_saved` | Was the brief successfully saved? |
| `professional_tone` | Was tone appropriate throughout? |

View evaluation results:
```bash
buyer-agent get-call <conversation_id>
```

Or in the [ElevenLabs dashboard](https://elevenlabs.io/app/agents) → Calls History.

## Data Collection

The agent automatically extracts structured data from conversations:

- `prospect_contact` — name, phone, email
- `budget_summary` — price range, finance status
- `location_summary` — preferred and excluded areas
- `property_summary` — type, beds, land size
- `timeline_summary` — when they want to buy

This data is available via:
1. The `save_buyer_brief` webhook tool (sent to your CRM)
2. Post-call webhook (conversation analysis)
3. ElevenLabs dashboard

## Webhook Handler

A sample webhook handler is included for receiving buyer briefs:

```bash
# Start the handler
uvicorn scripts.webhook_handler:app --port 3000

# Expose with ngrok for testing
ngrok http 3000

# Set the URL in .env
WEBHOOK_URL=https://abc123.ngrok.io/api/briefs
```

For production, integrate the webhook into your existing backend/CRM.

## Testing

### Browser Test (Fastest)

1. Deploy the agent: `buyer-agent deploy`
2. Go to [elevenlabs.io/app/agents](https://elevenlabs.io/app/agents)
3. Click your agent → "Test"
4. Have a conversation via browser microphone

### Simulation Test

```bash
# Run with default scenario
buyer-agent test <agent_id>

# Custom scenario
buyer-agent test <agent_id> -s "A downsizer looking to sell their 4-bed house and buy a 2-bed unit near the beach"
```

### Phone Test (Requires Twilio)

```bash
# 1. Set up Twilio
buyer-agent twilio-setup <agent_id>

# 2. Call a test number
buyer-agent call <agent_id> +614XXXXXXXX <phone_number_id> --name "Test User"

# 3. Check the call
buyer-agent list-calls
buyer-agent get-call <conversation_id> --transcript
```

## Custom Voice

To use a custom or cloned voice:

1. Go to [elevenlabs.io/app/voice-library](https://elevenlabs.io/app/voice-library)
2. Find or create a voice
3. Copy the Voice ID
4. Set in `.env`:
   ```bash
   ELEVENLABS_VOICE_ID=<your-voice-id>
   ```
5. Redeploy: `buyer-agent deploy -u <agent_id>`

### Recommended Voice Characteristics

For a buyer's agent assistant:
- Female voice (more approachable for this use case)
- Australian or neutral English accent
- Warm but professional tone
- Medium pace (not too fast)

## Buyer Brief Schema

The interview covers these areas (70+ fields when fully expanded):

| Section | Key Fields |
|---------|------------|
| **Contact** | Name, phone, email, preferred contact method |
| **Purchase Purpose** | Owner-occupier, investment, SMSF, development, holiday |
| **Budget & Finance** | Price range, stretch budget, deposit, pre-approval, FHOG/FHSS |
| **Location** | States, cities, suburbs, exclusions, commute, flood/bushfire zones |
| **Property** | Type, beds, baths, cars, land size, features, condition, strata |
| **Investment** | Strategy, yield, rent, depreciation, portfolio, subdivision |
| **Lifestyle** | Household, schools, childcare, priorities, deal-breakers |
| **Buying Process** | Timeline, auction comfort, solicitor, property to sell |

## Project Structure

```
elevenlabs-buyer-agent/
├── config/
│   └── settings.py              # Environment configuration
├── src/
│   ├── cli.py                   # CLI commands (buyer-agent)
│   ├── api_client.py            # ElevenLabs API wrapper
│   ├── agent_config.py          # Agent configuration builder
│   ├── workflow.py              # Workflow with subagents
│   └── prompts.py               # System prompts
├── scripts/
│   └── webhook_handler.py       # Sample webhook receiver
├── tests/
├── .env.example
├── pyproject.toml
└── README.md
```

## Cost Estimation

ElevenLabs pricing (as of 2024):
- **Starter**: $5/mo — 30 min voice
- **Creator**: $22/mo — 100 min voice
- **Pro**: $99/mo — 500 min voice
- **Scale**: $330/mo — 2000 min voice

Plus Twilio costs:
- Australian number: ~$4.50/mo
- Inbound: ~$0.0085/min
- Outbound: ~$0.085/min

For a buyer's agency doing 100 calls/month averaging 5 minutes:
- ElevenLabs: Creator plan ($22/mo)
- Twilio: ~$47/mo
- **Total: ~$70/month**

## Resources

- [ElevenLabs Agents Platform Docs](https://elevenlabs.io/docs/agents-platform/overview)
- [Create Agent API](https://elevenlabs.io/docs/agents-platform/api-reference/agents/create)
- [Twilio Integration](https://elevenlabs.io/docs/agents-platform/phone-numbers/twilio-integration/native-integration)
- [Agent Testing](https://elevenlabs.io/docs/agents-platform/customization/agent-testing)
- [Success Evaluation](https://elevenlabs.io/docs/agents-platform/customization/agent-analysis/success-evaluation)
- [Workflows](https://elevenlabs.io/docs/agents-platform/customization/agent-workflows)
