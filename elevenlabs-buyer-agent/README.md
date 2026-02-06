# ElevenLabs Voice Agent - Outbound Calling System

Three interfaces to trigger outbound calls using your ElevenLabs voice agent:

## 1. Web Dashboard

Modern web interface for managing prospects and campaigns.

```bash
cd web_dashboard
pip install -r ../requirements.txt
python app.py
```

Open http://localhost:5000

**Features:**
- Upload CSV files with prospects
- Add prospects manually
- Start/stop campaigns
- Real-time progress monitoring
- Call logs

---

## 2. Google Sheets Integration

Sync prospects from a Google Sheet and auto-call them.

### Setup

1. Create a Google Cloud Project
2. Enable Google Sheets API
3. Create a Service Account
4. Download `credentials.json`
5. Share your Sheet with the service account email

### Sheet Format

| Name | Phone | Email | Context | Status | Call Date | Conversation ID | Notes |
|------|-------|-------|---------|--------|-----------|-----------------|-------|
| John | +61... | john@... | Looking for... | pending | | | |

### Usage

```bash
# Set environment variables
export GOOGLE_SPREADSHEET_ID="your_spreadsheet_id"
export GOOGLE_CREDENTIALS_FILE="credentials.json"

# Run one-time campaign
python google_sheets_sync.py campaign

# Or watch for new prospects continuously
python google_sheets_sync.py watch
```

---

## 3. SMS/iMessage Trigger

Text commands to trigger calls from your phone.

### Setup

1. Get a Twilio phone number
2. Deploy this app (Heroku, Railway, or ngrok)
3. Set webhook URL in Twilio: `https://your-app.com/sms`

### SMS Commands

```
CALL John,+61400000001,Interested in Inner West
CALL +61400000001
STATUS
HELP
```

### Run Locally

```bash
pip install -r requirements.txt
python sms_trigger.py
```

For testing, use ngrok:
```bash
ngrok http 5001
```

---

## Environment Variables

```bash
# ElevenLabs
ELEVENLABS_API_KEY=your_key
ELEVENLABS_AGENT_ID=your_agent_id
AGENT_PHONE_NUMBER=+1234567890

# Twilio
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890

# Google Sheets
GOOGLE_SPREADSHEET_ID=your_sheet_id
GOOGLE_CREDENTIALS_FILE=credentials.json
```

---

## CSV Format

```csv
name,phone,email,context
John Smith,+61400000001,john@example.com,Looking for 3-bed in Sydney
Sarah Lee,+61400000002,sarah@example.com,First home buyer
```

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your credentials

# Option 1: Web Dashboard
python web_dashboard/app.py

# Option 2: Google Sheets
python google_sheets_sync.py watch

# Option 3: SMS
python sms_trigger.py
```
