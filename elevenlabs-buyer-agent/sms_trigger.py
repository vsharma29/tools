"""
SMS/iMessage Trigger for ElevenLabs Voice Agent
Receive SMS commands to trigger outbound calls

Setup:
1. Create a Twilio account
2. Get a phone number
3. Set the webhook URL to this app's /sms endpoint
4. Install: pip install flask twilio

SMS Commands:
    CALL John,+61400000001,Interested in Inner West
    CALL +61400000001
    STATUS
    HELP
"""

import os
import re
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from datetime import datetime
from outbound_caller import initiate_call

app = Flask(__name__)

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

# Authorized phone numbers (whitelist for security)
AUTHORIZED_NUMBERS = os.getenv('AUTHORIZED_NUMBERS', '').split(',')

# In-memory call log (use database in production)
call_log = []


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
                f"✓ Call connected to {prospect['name']}\nID: {result.get('conversation_id', 'N/A')}"
            )
        else:
            send_sms(
                from_number,
                f"✗ Call failed to {prospect['name']}\nError: {result.get('error', 'Unknown')}"
            )

    elif command == 'STATUS':
        # Return recent call status
        if not call_log:
            resp.message("No calls made yet.")
        else:
            recent = call_log[-5:]  # Last 5 calls
            status_lines = []
            for log in recent:
                status = "✓" if log['result']['success'] else "✗"
                name = log['prospect']['name']
                time = log['timestamp'].split('T')[1][:5]
                status_lines.append(f"{status} {time} {name}")

            resp.message("Recent calls:\n" + "\n".join(status_lines))

    elif command == 'HELP':
        resp.message(
            "Voice Agent SMS Commands:\n\n"
            "CALL Name,+61...,Context\n"
            "  → Initiate a call\n\n"
            "CALL +61...\n"
            "  → Quick call (no name)\n\n"
            "STATUS\n"
            "  → View recent calls\n\n"
            "HELP\n"
            "  → Show this message"
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
    return {'status': 'ok', 'timestamp': datetime.now().isoformat()}


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
    print("""
SMS Trigger for Voice Agent

Setup:
1. Set environment variables:
   - TWILIO_ACCOUNT_SID
   - TWILIO_AUTH_TOKEN
   - TWILIO_PHONE_NUMBER
   - AUTHORIZED_NUMBERS (comma-separated, optional)
   - ELEVENLABS_API_KEY
   - ELEVENLABS_AGENT_ID
   - AGENT_PHONE_NUMBER

2. Deploy this app (e.g., to Heroku, Railway, or ngrok for testing)

3. In Twilio Console, set your phone number's webhook to:
   https://your-app.com/sms

4. Text your Twilio number:
   CALL John,+61400000001,Interested in Inner West

SMS Commands:
   CALL Name,+Phone,Context  - Initiate a call
   STATUS                    - View recent calls
   HELP                      - Show help
    """)

    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
