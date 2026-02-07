# ElevenLabs Buyer Agent

A complete voice agent system for real estate buyer inquiries, powered by ElevenLabs Conversational AI and Twilio.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Inbound Call  │────▶│     Twilio      │────▶│   ElevenLabs    │
│  (Prospect)     │     │  +61485027700   │     │   Voice Agent   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               │ SMS
                               ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │   SMS Trigger   │────▶│  Outbound Call  │
                        │   (Your Team)   │     │  (To Prospect)  │
                        └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  Memory Service │
                        │     (Mem0)      │
                        └─────────────────┘
```

## Deployed Services

| Service | URL | Purpose |
|---------|-----|---------|
| Web Dashboard | https://webdashboard-navy.vercel.app | Upload CSV, manage campaigns |
| SMS/Voice Trigger | https://smstrigger.vercel.app | Text/call to trigger outbound calls |
| Memory Service | https://memoryservice.vercel.app | Persistent caller memory via Mem0 |

## Quick Start

### 1. Prerequisites

- Twilio account with phone number
- ElevenLabs account with Conversational AI access
- Vercel account (for deployments)
- Mem0 account (for memory, optional)

### 2. Connect Twilio to ElevenLabs (Required First Step)

**This must be done in ElevenLabs before webhooks will work:**

1. Go to https://elevenlabs.io/app/conversational-ai
2. Select your agent → **Phone Numbers** tab
3. Click **Connect Twilio**
4. Enter your Twilio credentials:
   - Account SID: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - Auth Token: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
5. Click **Import Phone Numbers**
6. Select your Twilio number to link it to the agent

This syncs your Twilio number with ElevenLabs and auto-configures the voice webhook.

### 3. Configure SMS Webhook (For Trigger Service)

After connecting Twilio to ElevenLabs, add the SMS webhook:

```bash
# Using the configuration script
python scripts/configure_twilio.py --update-webhooks \
  --sms-url "https://smstrigger.vercel.app/sms"
```

Or manually in Twilio Console:
1. Go to https://console.twilio.com/phone-numbers
2. Click your number
3. Under "Messaging" → "A Message Comes In"
4. Set webhook URL: `https://smstrigger.vercel.app/sms`

### 4. Set Environment Variables (Vercel)

**For SMS Trigger:**
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+61485027700
ELEVENLABS_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ELEVENLABS_AGENT_ID=agent_xxxxxxxxxxxxxxxxxxxxxxxx
AGENT_PHONE_NUMBER=pn_xxxxxxxx  # ElevenLabs phone ID for outbound
AUTHORIZED_NUMBERS=+61400111222,+61400333444  # Optional whitelist
```

**For Memory Service:**
```
MEM0_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Usage

### Inbound Calls (Prospects → Agent)

Prospects call your Twilio number → ElevenLabs agent answers automatically.

```
+61 485 027 700  →  ElevenLabs Buyer Agent
```

### Outbound Calls via SMS

Text your Twilio number:

```
CALL John,+61400123456,Interested in Inner West
CALL +61400123456
STATUS
HELP
```

### Outbound Calls via Voice

Call the trigger number and speak naturally:

```
"Call John at 0400 123 456 about the Inner West property"
"Call 0412 345 678"
```

### Outbound Calls via Web Dashboard

1. Go to https://webdashboard-navy.vercel.app
2. Upload CSV with prospects
3. Click "Start Campaign"

## CSV Format

```csv
name,phone,context
John Smith,+61400123456,Interested in 3-bed house Inner West
Sarah Jones,+61400234567,Budget $1.5M looking in Bondi
```

## Memory Integration (Mem0)

Enable the agent to remember past interactions per caller.

### Add Memory Tools to ElevenLabs Agent

1. Go to your agent → **Tools** section

2. Add `retrieveMemories`:
```json
{
  "name": "retrieveMemories",
  "description": "Retrieve relevant information from past conversations with this caller",
  "webhook_url": "https://memoryservice.vercel.app/tools/retrieveMemories",
  "parameters": {
    "type": "object",
    "properties": {
      "query": { "type": "string" }
    },
    "required": ["query"]
  }
}
```

3. Add `addMemories`:
```json
{
  "name": "addMemories",
  "description": "Store important information to remember for future calls",
  "webhook_url": "https://memoryservice.vercel.app/tools/addMemories",
  "parameters": {
    "type": "object",
    "properties": {
      "message": { "type": "string" }
    },
    "required": ["message"]
  }
}
```

4. Update agent system prompt:
```
At the start of each call, use retrieveMemories to check for past interactions.
When the caller shares preferences, requirements, or important details, use addMemories to save them.
```

## Twilio Configuration Script

```bash
# Interactive setup wizard
python scripts/configure_twilio.py --setup

# Check current configuration
python scripts/configure_twilio.py --status

# View recent calls
python scripts/configure_twilio.py --calls

# Check errors for a failed call
python scripts/configure_twilio.py --errors CA1234567890abcdef

# Update webhooks
python scripts/configure_twilio.py --update-webhooks \
  --sms-url "https://smstrigger.vercel.app/sms"
```

## Troubleshooting

### Error 21264: From Phone Number Not Verified

**Cause:** Twilio trial account restriction.

**Fix:**
- Verify calling number at https://console.twilio.com/verified-caller-ids
- Or upgrade to paid Twilio account

### Error 11200: HTTP 502 from ElevenLabs

**Cause:** ElevenLabs webhook not responding.

**Fix:**
1. Ensure Twilio is connected via ElevenLabs Phone Numbers section first
2. Use main endpoint `api.elevenlabs.io` (not regional like `api.au.elevenlabs.io`)
3. Verify agent ID is correct

### Calls connecting but agent doesn't respond

**Cause:** Twilio not properly linked to ElevenLabs.

**Fix:**
1. Go to ElevenLabs → Conversational AI → Phone Numbers
2. Disconnect and reconnect Twilio
3. Re-import your phone number
4. Test inbound call again

### SMS trigger not working

**Cause:** Missing environment variables or wrong webhook.

**Fix:**
1. Verify SMS webhook is set to `https://smstrigger.vercel.app/sms`
2. Check Vercel environment variables are set
3. Redeploy: `cd sms_trigger && vercel --prod`

## File Structure

```
elevenlabs-buyer-agent/
├── README.md
├── requirements.txt
├── .env.example
├── outbound_caller.py          # Core outbound calling module
├── google_sheets_sync.py       # Google Sheets integration
├── scripts/
│   └── configure_twilio.py     # Twilio configuration script
├── web_dashboard/
│   ├── app.py                  # Flask web dashboard
│   ├── templates/
│   │   └── dashboard.html
│   ├── vercel.json
│   └── requirements.txt
├── sms_trigger/
│   ├── app.py                  # SMS & voice trigger service
│   ├── vercel.json
│   └── requirements.txt
└── memory_service/
    ├── app.py                  # Mem0 webhook handler
    ├── ELEVENLABS_SETUP.md
    ├── vercel.json
    └── requirements.txt
```

## Credentials Reference

| Service | Credential | Where to Find |
|---------|------------|---------------|
| Twilio | Account SID | https://console.twilio.com |
| Twilio | Auth Token | https://console.twilio.com |
| ElevenLabs | API Key | https://elevenlabs.io/app/settings/api-keys |
| ElevenLabs | Agent ID | Agent settings or URL |
| Mem0 | API Key | https://app.mem0.ai |
| Vercel | Token | https://vercel.com/account/tokens |

## Deployment

Each service is deployed on Vercel. To redeploy after changes:

```bash
cd web_dashboard && vercel --prod
cd sms_trigger && vercel --prod
cd memory_service && vercel --prod
```

## Security Notes

- **AUTHORIZED_NUMBERS**: Whitelist for SMS/voice trigger access (your team only)
- **API Keys**: Store in Vercel environment variables, never commit to code
- **Twilio Trial**: Only verified numbers can call - upgrade for production
- **Separate Numbers**: Use different Twilio numbers for inbound (prospects) vs trigger (your team)
