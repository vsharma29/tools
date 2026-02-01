# Buyer Voice Agent

Voice AI agent for an Australian residential buyer's agency. Conducts phone interviews with prospects to generate comprehensive buyer briefs.

Built with **Claude (Anthropic SDK)** for conversation intelligence, with provider-agnostic audio (STT/TTS) and a plug-in telephony layer ready for outbound/inbound mobile calls.

## Architecture

```
┌─────────────┐     ┌──────────┐     ┌─────────────┐     ┌──────────┐
│  Phone Call  │◄───►│  Twilio  │◄───►│  FastAPI +   │◄───►│  Claude  │
│  (Mobile)    │     │  Media   │     │  Voice       │     │  Agent   │
│              │     │  Streams │     │  Pipeline    │     │  SDK     │
└─────────────┘     └──────────┘     └──────┬───────┘     └──────────┘
                                            │
                                    ┌───────┴───────┐
                                    │               │
                               ┌────▼────┐    ┌─────▼─────┐
                               │ STT     │    │ TTS       │
                               │ Deepgram│    │ Cartesia  │
                               │ Whisper │    │ OpenAI    │
                               └─────────┘    │ ElevenLabs│
                                              └───────────┘
                                                    │
                                            ┌───────▼───────┐
                                            │  Output       │
                                            │  S3 + Webhook │
                                            └───────────────┘
```

## Latency Optimisation

The pipeline is designed for sub-second turn latency:

1. **Sentence-level streaming** — Claude streams text; each sentence is immediately dispatched to TTS without waiting for the full response.
2. **TTS pipelining** — TTS synthesis starts on sentence N while sentence N-1 audio is still being played to the caller.
3. **Deepgram Nova-2** — Streaming STT with ~200ms endpointing for fast utterance detection.
4. **Cartesia Sonic** — Sub-200ms time-to-first-byte TTS.
5. **Barge-in interruption** — Energy-based VAD monitors incoming audio during TTS playback. When the caller speaks, TTS is cancelled via `asyncio.Event`, Twilio's playback buffer is cleared, and the caller's audio is processed immediately.

## Quick Start

### 1. Install dependencies

```bash
cd voice-agent
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

**Minimum required keys:**
- `ANTHROPIC_API_KEY` — for Claude
- `DEEPGRAM_API_KEY` — for STT (or `OPENAI_API_KEY` if using Whisper)
- `CARTESIA_API_KEY` — for TTS (or swap provider)

### 3. Run locally (text mode — no audio keys needed)

```bash
uvicorn src.api:app --reload --port 8000
```

Test with curl:
```bash
# Create a session
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"prospect_name": "Jane Smith", "agency_name": "Sydney Buyers Co"}'

# Send a text turn
curl -X POST http://localhost:8000/api/turns/text \
  -H "Content-Type: application/json" \
  -d '{"session_id": "SESSION_ID_HERE", "text": "Hi, I am looking for an investment property"}'
```

### 4. Run tests

```bash
pytest tests/ -v
```

## Testing Guide

### Level 1: Unit tests (no API keys needed)

```bash
pytest tests/ -v
```

This runs:
- **test_guardrails.py** — input/output guardrail rules, sensitive data blocking, abuse detection
- **test_schema.py** — buyer brief serialisation/deserialisation
- **test_vad.py** — VAD energy detection, barge-in triggering, buffer management, edge cases

### Level 2: Barge-in simulation (no API keys needed)

```bash
python scripts/test_barge_in.py
```

Runs a full barge-in lifecycle with synthetic PCM audio:
1. Calibrates VAD from silence
2. Verifies no false triggers during silence
3. Simulates caller interruption → verifies cancel_event fires
4. Verifies buffered audio is collected
5. Verifies clean next turn

### Level 3: Text-mode interview (needs ANTHROPIC_API_KEY only)

```bash
# Terminal 1
ANTHROPIC_API_KEY=sk-ant-... uvicorn src.api:app --port 8000

# Terminal 2
python scripts/test_text_interview.py
```

Interactive conversation with Ava. Tests the full Claude agent loop including:
- Interview flow (greeting → questions → brief generation)
- Guardrails (try typing a credit card number or abusive language)
- Tool calling (save_buyer_brief, transfer_to_human)
- Brief output as JSON

Sample conversation to test:
```
You: Hi, I'm looking for an investment property
You: Budget is 600 to 800k, I have pre-approval
You: Looking at western Sydney, maybe Penrith or Blacktown area
You: I want a house, at least 3 bedrooms, 600sqm land minimum
You: Cash flow focused, want at least 5% yield
You: Couple with one kid, need good schools nearby
You: Ready to buy in the next 3 months
You: That sounds right, nothing else to add
```

### Level 4: WebSocket interview (needs ANTHROPIC_API_KEY only)

```bash
# Terminal 1
ANTHROPIC_API_KEY=sk-ant-... uvicorn src.api:app --port 8000

# Terminal 2
pip install websockets
python scripts/test_websocket.py
```

Same as Level 3 but over a persistent WebSocket connection (closer to production flow).

### Level 5: Full voice with Twilio (needs all API keys)

Requires: `ANTHROPIC_API_KEY`, `DEEPGRAM_API_KEY`, `CARTESIA_API_KEY`, `TWILIO_*` keys.

```bash
# Start with ngrok for public URL
ngrok http 8000

# Start server
cp .env.example .env  # fill in all keys
uvicorn src.api:app --port 8000

# Trigger an outbound call
curl -X POST http://localhost:8000/api/calls/outbound \
  -H "Content-Type: application/json" \
  -d '{"to_number": "+61400000000", "prospect_name": "Jane Smith"}'
```

### Testing guardrails specifically

```bash
# In a Level 3+ session, try these inputs:
"My TFN is 12345678"              → Should block and redirect
"My card is 4111 2222 3333 4444"  → Should block and redirect
"What about bitcoin?"             → Should warn, steer back (2x → terminate)
"This is bullshit"                → Should warn (2x → terminate)
```

### Testing barge-in specifically

In a Level 5 (Twilio) session:
1. Let Ava start her greeting
2. Interrupt her mid-sentence by speaking
3. Verify: her audio stops immediately and she processes your words
4. Check metrics: `GET /api/sessions/{id}/metrics` should show `barge_in_count > 0`

## Adding a Mobile Phone Provider (Twilio)

This is the step-by-step guide to enable the agent to **call prospects on their mobile phones** and conduct interviews as a human agent would.

### Step 1: Create a Twilio account
- Sign up at https://www.twilio.com
- Verify your account (requires credit card for Australian numbers)

### Step 2: Buy an Australian phone number
- Go to Twilio Console → Phone Numbers → Buy a Number
- Select Australia (+61) and choose a number with **Voice** capability
- Cost: ~$4.50 AUD/month

### Step 3: Set environment variables
```bash
TELEPHONY_PROVIDER=twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+61XXXXXXXXX
```

### Step 4: Deploy with a public URL
Twilio needs a publicly accessible URL for webhooks and media streams.

**For development:** Use ngrok
```bash
ngrok http 8000
# Note the https URL, e.g. https://abc123.ngrok.io
```

**For production:** Deploy to AWS (see below) or any host with a public domain + SSL.

### Step 5: Configure Twilio webhooks
In Twilio Console → Phone Numbers → your number → Voice Configuration:
- **A call comes in:** Webhook → `https://your-domain/api/telephony/twilio/incoming` (POST)
- **Status callback:** `https://your-domain/api/telephony/twilio/status` (POST)

### Step 6: Make an outbound call
```bash
curl -X POST https://your-domain/api/calls/outbound \
  -H "Content-Type: application/json" \
  -d '{
    "to_number": "+61400000000",
    "prospect_name": "Jane Smith",
    "agency_name": "Sydney Buyers Co"
  }'
```

### Step 7: Handle follow-up calls
The agent can schedule follow-ups via the `schedule_followup` tool. Integrate with your CRM or use a cron job to trigger outbound calls at the scheduled time:

```python
# Example: trigger follow-up from your scheduler
import httpx

httpx.post("https://your-domain/api/calls/outbound", json={
    "to_number": "+61400000000",
    "prospect_name": "Jane Smith",
})
```

### WebSocket note for production
Twilio Media Streams use WebSockets for real-time bidirectional audio. AWS Lambda **does not support WebSockets natively**. For production with phone calls, choose one of:

| Option | WebSocket Support | Cost | Complexity |
|--------|------------------|------|------------|
| **ECS Fargate** (recommended) | Native | ~$30/month | Medium |
| **EC2 / Lightsail** | Native | ~$10/month | Low |
| **API Gateway WebSocket API** | Via Lambda | Pay-per-message | High |

The REST API (sessions, text turns, briefs) runs fine on Lambda. Only the media stream endpoint needs persistent connections.

### Switching to Vonage or Telnyx
The telephony layer is provider-agnostic. To add a new provider:
1. Create `src/telephony/vonage_provider.py` implementing `TelephonyProvider`
2. Add the provider to `src/telephony/factory.py`
3. Set `TELEPHONY_PROVIDER=vonage` in `.env`

## Serverless Deployment (AWS SAM)

```bash
# Build
cd infra
sam build --template template.yaml

# Deploy (first time — guided)
sam deploy --guided \
  --parameter-overrides \
    AnthropicApiKey=sk-ant-... \
    DeepgramApiKey=... \
    CartesiaApiKey=...

# Subsequent deploys
sam deploy
```

## Buyer Brief Schema

The interview covers these sections (all fields optional — the agent fills what it gathers):

| Section | Key Fields |
|---------|-----------|
| **Contact** | Name, phone, email, preferred contact method |
| **Purchase Purpose** | Owner-occupier, investment, SMSF, development, holiday |
| **Budget & Finance** | Price range, stretch budget, deposit, pre-approval, FHOG/FHSS, stamp duty |
| **Location** | States, cities, suburbs, regions, exclusions, commute, flood/bushfire zones |
| **Property** | Type, beds, baths, cars, land size, frontage, pool, condition, heritage, strata |
| **Investment** | Cash flow vs capital growth, yield target, rent, depreciation, portfolio, subdivision |
| **Lifestyle** | Household composition, schools, childcare, lifestyle priorities, deal-breakers |
| **Buying Process** | Timeline, auction comfort, offers made, solicitor, property to sell |

## Guardrails

Built-in safety:
- **No sensitive data**: Blocks TFN, credit card, BSB numbers
- **No professional advice**: Flags guarantee language, financial/legal advice
- **Abuse detection**: Warns then terminates on repeated abuse
- **Off-topic detection**: Warns then terminates persistent off-topic chat
- **Call duration cap**: 15-minute safety limit (configurable)
- **Content filtering**: Output scanned before TTS for prohibited patterns

## Project Structure

```
voice-agent/
├── config/settings.py          # Centralised config from env
├── handler.py                  # Lambda entry point (Mangum)
├── src/
│   ├── api.py                  # FastAPI app (REST + WebSocket)
│   ├── agent/
│   │   ├── interview_agent.py  # Core Claude agent with streaming
│   │   ├── voice_pipeline.py   # STT → Agent → TTS orchestrator
│   │   ├── prompts.py          # System prompt and greeting templates
│   │   └── tools.py            # Claude tool definitions
│   ├── audio/
│   │   ├── base.py             # STT/TTS abstract interfaces (cancel_event support)
│   │   ├── vad.py              # Voice Activity Detection + BargeInManager
│   │   ├── deepgram_stt.py     # Deepgram Nova-2 adapter
│   │   ├── whisper_stt.py      # OpenAI Whisper adapter
│   │   ├── cartesia_tts.py     # Cartesia Sonic adapter (cancellable)
│   │   ├── openai_tts.py       # OpenAI TTS adapter (cancellable)
│   │   ├── elevenlabs_tts.py   # ElevenLabs adapter (cancellable)
│   │   └── factory.py          # Provider factory
│   ├── telephony/
│   │   ├── base.py             # Telephony abstract interface
│   │   ├── twilio_provider.py  # Twilio + Media Streams
│   │   └── factory.py          # Provider factory
│   ├── guardrails/
│   │   └── guardrails.py       # Input/output/duration guardrails
│   ├── output/
│   │   └── handlers.py         # S3 + webhook brief delivery
│   └── schemas/
│       └── buyer_brief.py      # Pydantic models (exhaustive)
├── tests/
│   ├── test_guardrails.py      # Guardrail unit tests
│   ├── test_schema.py          # Brief schema tests
│   └── test_vad.py             # VAD + barge-in tests
├── scripts/
│   ├── test_text_interview.py  # Interactive text-mode test (HTTP)
│   ├── test_websocket.py       # Interactive WebSocket test
│   └── test_barge_in.py        # Standalone barge-in simulation
├── infra/template.yaml         # AWS SAM template
├── Dockerfile                  # Container deployment
└── pyproject.toml
```
