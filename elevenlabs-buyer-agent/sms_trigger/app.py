"""
SMS/iMessage Trigger for ElevenLabs Voice Agent
Deployed on Vercel - Receive SMS commands to trigger outbound calls

SMS Commands:
    CALL John,+61400000001,Interested in Inner West
    CALL +61400000001
    STATUS
    HELP
"""

import os
import re
import requests
from flask import Flask, request, Response, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from datetime import datetime

app = Flask(__name__)

# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
ELEVENLABS_AGENT_ID = os.getenv('ELEVENLABS_AGENT_ID')
AGENT_PHONE_NUMBER = os.getenv('AGENT_PHONE_NUMBER')

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

# Authorized phone numbers (whitelist for security)
AUTHORIZED_NUMBERS = os.getenv('AUTHORIZED_NUMBERS', '').split(',')

# In-memory call log (resets on cold start - use database for production)
call_log = []


def initiate_call(prospect: dict) -> dict:
    """
    Initiate an outbound call via ElevenLabs Conversational AI
    """
    url = f"https://api.elevenlabs.io/v1/convai/conversations/call"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    # Build dynamic context for the agent
    context = f"You are calling {prospect.get('name', 'a potential buyer')}."
    if prospect.get('context'):
        context += f" Background: {prospect['context']}"

    payload = {
        "agent_id": ELEVENLABS_AGENT_ID,
        "agent_phone_number": AGENT_PHONE_NUMBER,
        "customer_phone_number": prospect['phone'],
        "conversation_initiation_client_data": {
            "dynamic_variables": {
                "prospect_name": prospect.get('name', 'there'),
                "context": prospect.get('context', ''),
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'conversation_id': data.get('conversation_id'),
                'call_sid': data.get('call_sid'),
                'response': data
            }
        else:
            return {
                'success': False,
                'error': f"API Error {response.status_code}: {response.text}",
                'status_code': response.status_code
            }

    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Request timed out'}
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': str(e)}


def is_authorized(phone_number: str) -> bool:
    """Check if the sender is authorized to use the bot"""
    # If no whitelist is set, allow all
    if not AUTHORIZED_NUMBERS or AUTHORIZED_NUMBERS == ['']:
        return True
    # Normalize phone numbers for comparison
    normalized = phone_number.replace(' ', '').replace('-', '')
    return any(
        normalized.endswith(auth.replace(' ', '').replace('-', ''))
        for auth in AUTHORIZED_NUMBERS
    )


def parse_call_command(message: str) -> dict:
    """
    Parse CALL command from SMS

    Formats supported:
        CALL John,+61400000001,Looking for 3-bed house
        CALL John,+61400000001
        CALL +61400000001
    """
    # Remove 'CALL ' prefix
    content = message[5:].strip()

    parts = [p.strip() for p in content.split(',')]

    if len(parts) >= 3:
        return {
            'name': parts[0],
            'phone': parts[1],
            'context': ','.join(parts[2:])  # Join remaining parts as context
        }
    elif len(parts) == 2:
        return {
            'name': parts[0],
            'phone': parts[1],
            'context': ''
        }
    elif len(parts) == 1:
        # Just a phone number
        return {
            'name': 'Unknown',
            'phone': parts[0],
            'context': ''
        }

    return None


def send_sms(to: str, message: str):
    """Send an SMS using Twilio"""
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    client.messages.create(
        body=message,
        from_=TWILIO_PHONE_NUMBER,
        to=to
    )


@app.route('/')
def index():
    """Landing page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SMS Trigger - Voice Agent</title>
        <style>
            body { font-family: system-ui, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #000; color: #fff; }
            h1 { border-bottom: 2px solid #fff; padding-bottom: 10px; }
            code { background: #222; padding: 2px 8px; border-radius: 4px; }
            .command { background: #111; padding: 15px; border-radius: 8px; margin: 10px 0; border: 1px solid #333; }
            .status { color: #0f0; }
        </style>
    </head>
    <body>
        <h1>SMS Trigger for Voice Agent</h1>
        <p class="status">Status: Active</p>

        <h2>SMS Commands</h2>
        <div class="command">
            <code>CALL Name,+61400000001,Context</code>
            <p>Initiate a call to a prospect</p>
        </div>
        <div class="command">
            <code>CALL +61400000001</code>
            <p>Quick call (no name/context)</p>
        </div>
        <div class="command">
            <code>STATUS</code>
            <p>View recent calls</p>
        </div>
        <div class="command">
            <code>HELP</code>
            <p>Show available commands</p>
        </div>

        <h2>Setup</h2>
        <p>Point your Twilio webhook to: <code>/sms</code></p>
    </body>
    </html>
    """


@app.route('/sms', methods=['POST'])
def handle_sms():
    """Handle incoming SMS messages"""
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')

    resp = MessagingResponse()

    # Check authorization
    if not is_authorized(from_number):
        resp.message("You are not authorized to use this service.")
        return Response(str(resp), mimetype='application/xml')

    # Parse command
    command = incoming_msg.upper().split()[0] if incoming_msg else ''

    if command == 'CALL':
        # Parse and initiate call
        prospect = parse_call_command(incoming_msg)

        if not prospect:
            resp.message("Invalid format. Use: CALL Name,+61400000001,Context")
            return Response(str(resp), mimetype='application/xml')

        # Validate phone number
        if not re.match(r'^\+?[1-9]\d{6,14}$', prospect['phone'].replace(' ', '')):
            resp.message(f"Invalid phone number: {prospect['phone']}")
            return Response(str(resp), mimetype='application/xml')

        # Initiate the call
        resp.message(f"Initiating call to {prospect['name']} at {prospect['phone']}...")

        result = initiate_call(prospect)

        # Log the call
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'triggered_by': from_number,
            'prospect': prospect,
            'result': result
        }
        call_log.append(log_entry)

        # Send result as follow-up SMS
        if result['success']:
            send_sms(
                from_number,
                f"Call connected to {prospect['name']}\nID: {result.get('conversation_id', 'N/A')}"
            )
        else:
            send_sms(
                from_number,
                f"Call failed to {prospect['name']}\nError: {result.get('error', 'Unknown')}"
            )

    elif command == 'STATUS':
        # Return recent call status
        if not call_log:
            resp.message("No calls made yet.")
        else:
            recent = call_log[-5:]  # Last 5 calls
            status_lines = []
            for log in recent:
                status = "OK" if log['result']['success'] else "FAIL"
                name = log['prospect']['name']
                time = log['timestamp'].split('T')[1][:5]
                status_lines.append(f"{status} {time} {name}")

            resp.message("Recent calls:\n" + "\n".join(status_lines))

    elif command == 'HELP':
        resp.message(
            "Voice Agent SMS Commands:\n\n"
            "CALL Name,+61...,Context\n"
            "  > Initiate a call\n\n"
            "CALL +61...\n"
            "  > Quick call (no name)\n\n"
            "STATUS\n"
            "  > View recent calls\n\n"
            "HELP\n"
            "  > Show this message"
        )

    else:
        resp.message(
            f"Unknown command: {command}\n\n"
            "Commands: CALL, STATUS, HELP\n"
            "Reply HELP for details."
        )

    return Response(str(resp), mimetype='application/xml')


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'sms-trigger',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """API endpoint to retrieve call logs"""
    return jsonify({
        'logs': call_log[-50:],  # Return last 50 entries
        'total': len(call_log)
    })


# Webhook for call status updates (optional)
@app.route('/call-status', methods=['POST'])
def call_status_webhook():
    """Receive call status updates from Twilio"""
    call_sid = request.values.get('CallSid')
    call_status = request.values.get('CallStatus')
    duration = request.values.get('CallDuration', 0)

    print(f"Call {call_sid}: {call_status} (duration: {duration}s)")

    # Find and update the call log
    for log in call_log:
        if log['result'].get('call_sid') == call_sid:
            log['call_status'] = call_status
            log['duration'] = duration
            break

    return '', 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
