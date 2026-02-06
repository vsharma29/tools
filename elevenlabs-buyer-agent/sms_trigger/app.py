"""
SMS & Voice Trigger for ElevenLabs Voice Agent
Deployed on Vercel - Receive SMS or voice commands to trigger outbound calls

SMS Commands:
    CALL John,+61400000001,Interested in Inner West
    CALL +61400000001
    STATUS
    HELP

Voice Commands (call and speak):
    "Call John at 0400 000 001 about the Inner West property"
    "Call 0400 000 001"
"""

import os
import re
import requests
from flask import Flask, request, Response, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
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


def parse_voice_command(transcription: str) -> dict:
    """
    Parse voice transcription to extract call details

    Examples:
        "Call John at 0400 000 001 about the Inner West property"
        "Call 0412345678"
        "Please call Sarah at plus 61 400 123 456 she's interested in Bondi"
    """
    text = transcription.lower().strip()

    # Extract phone number - look for digit sequences
    # Handle spoken numbers like "0 4 0 0" or "zero four hundred"
    phone_match = re.search(r'(?:at\s+)?(\+?\d[\d\s\-]{7,20}\d)', text)

    if not phone_match:
        # Try to find numbers with spaces between digits
        digits = re.findall(r'\d', text)
        if len(digits) >= 8:
            phone = ''.join(digits[-10:]) if len(digits) >= 10 else ''.join(digits)
        else:
            return None
    else:
        phone = re.sub(r'[\s\-]', '', phone_match.group(1))

    # Extract name - look for patterns like "call [name] at"
    name_match = re.search(r'call\s+([a-z]+)\s+(?:at|on|phone)', text)
    name = name_match.group(1).title() if name_match else 'Unknown'

    # Extract context - everything after "about" or "regarding"
    context_match = re.search(r'(?:about|regarding|for|interested in)\s+(.+?)(?:\.|$)', text)
    context = context_match.group(1) if context_match else ''

    return {
        'name': name,
        'phone': phone if phone.startswith('+') else f'+61{phone.lstrip("0")}',  # Default to AU
        'context': context
    }


def process_command(message: str, from_number: str, source: str = 'sms') -> dict:
    """
    Process a command from SMS or voice transcription
    Returns dict with 'response' text and 'success' bool
    """
    # Parse command
    command = message.upper().split()[0] if message else ''

    if command == 'CALL':
        prospect = parse_call_command(message)

        if not prospect:
            return {
                'success': False,
                'response': "Invalid format. Use: CALL Name,+61400000001,Context"
            }

        # Validate phone number
        if not re.match(r'^\+?[1-9]\d{6,14}$', prospect['phone'].replace(' ', '')):
            return {
                'success': False,
                'response': f"Invalid phone number: {prospect['phone']}"
            }

        # Initiate the call
        result = initiate_call(prospect)

        # Log the call
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'triggered_by': from_number,
            'source': source,
            'prospect': prospect,
            'result': result
        }
        call_log.append(log_entry)

        if result['success']:
            return {
                'success': True,
                'response': f"Call initiated to {prospect['name']} at {prospect['phone']}"
            }
        else:
            return {
                'success': False,
                'response': f"Call failed: {result.get('error', 'Unknown error')}"
            }

    elif command == 'STATUS':
        if not call_log:
            return {'success': True, 'response': "No calls made yet."}

        recent = call_log[-5:]
        status_lines = []
        for log in recent:
            status = "OK" if log['result']['success'] else "FAIL"
            name = log['prospect']['name']
            time = log['timestamp'].split('T')[1][:5]
            status_lines.append(f"{status} {time} {name}")

        return {'success': True, 'response': "Recent calls:\n" + "\n".join(status_lines)}

    elif command == 'HELP':
        return {
            'success': True,
            'response': "Commands: CALL Name,+61...,Context | STATUS | HELP"
        }

    else:
        # Try to parse as natural language voice command
        prospect = parse_voice_command(message)
        if prospect and prospect.get('phone'):
            result = initiate_call(prospect)

            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'triggered_by': from_number,
                'source': source,
                'prospect': prospect,
                'result': result
            }
            call_log.append(log_entry)

            if result['success']:
                return {
                    'success': True,
                    'response': f"Call initiated to {prospect['name']} at {prospect['phone']}"
                }
            else:
                return {
                    'success': False,
                    'response': f"Call failed: {result.get('error', 'Unknown error')}"
                }

        return {
            'success': False,
            'response': f"Unknown command. Say: Call [name] at [phone number] about [context]"
        }


@app.route('/')
def index():
    """Landing page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SMS & Voice Trigger - Voice Agent</title>
        <style>
            body { font-family: system-ui, sans-serif; max-width: 700px; margin: 50px auto; padding: 20px; background: #000; color: #fff; }
            h1 { border-bottom: 2px solid #fff; padding-bottom: 10px; }
            h2 { margin-top: 30px; color: #aaa; }
            code { background: #222; padding: 2px 8px; border-radius: 4px; font-size: 14px; }
            .command { background: #111; padding: 15px; border-radius: 8px; margin: 10px 0; border: 1px solid #333; }
            .command p { margin: 5px 0 0 0; color: #888; font-size: 14px; }
            .status { color: #0f0; }
            .section { margin: 30px 0; padding: 20px; background: #0a0a0a; border-radius: 12px; }
            .section h3 { margin-top: 0; color: #fff; }
            .badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; margin-left: 10px; }
            .badge-sms { background: #1a4; }
            .badge-voice { background: #14a; }
            .setup-item { margin: 10px 0; padding: 10px; background: #111; border-radius: 6px; }
        </style>
    </head>
    <body>
        <h1>SMS & Voice Trigger</h1>
        <p class="status">Status: Active</p>
        <p>Trigger outbound calls via text message or voice command</p>

        <div class="section">
            <h3>SMS Commands <span class="badge badge-sms">TEXT</span></h3>
            <div class="command">
                <code>CALL Name,+61400000001,Context</code>
                <p>Full format with name and context</p>
            </div>
            <div class="command">
                <code>CALL +61400000001</code>
                <p>Quick call with just phone number</p>
            </div>
            <div class="command">
                <code>STATUS</code>
                <p>View recent call history</p>
            </div>
            <div class="command">
                <code>HELP</code>
                <p>Show available commands</p>
            </div>
        </div>

        <div class="section">
            <h3>Voice Commands <span class="badge badge-voice">CALL</span></h3>
            <p style="color:#888;">Call the Twilio number and speak naturally:</p>
            <div class="command">
                <code>"Call John at 0400 123 456 about the Inner West property"</code>
                <p>Natural language with name, number, and context</p>
            </div>
            <div class="command">
                <code>"Call 0412 345 678"</code>
                <p>Quick call with just the phone number</p>
            </div>
            <div class="command">
                <code>"Call Sarah, she's interested in Bondi, her number is 0400 111 222"</code>
                <p>Flexible word order - just include the details</p>
            </div>
        </div>

        <h2>Twilio Setup</h2>
        <div class="setup-item">
            <strong>SMS Webhook:</strong> <code>/sms</code> (POST)
        </div>
        <div class="setup-item">
            <strong>Voice Webhook:</strong> <code>/voice</code> (POST)
        </div>
        <div class="setup-item">
            <strong>Voicemail Transcription:</strong> <code>/voice/recording</code> (POST)
        </div>

        <h2>Environment Variables</h2>
        <div style="font-size: 13px; color: #666;">
            ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID, AGENT_PHONE_NUMBER,<br>
            TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER,<br>
            AUTHORIZED_NUMBERS (optional, comma-separated whitelist)
        </div>
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

    # Process the command
    result = process_command(incoming_msg, from_number, source='sms')
    resp.message(result['response'])

    # Send follow-up SMS for call results
    if 'Call initiated' in result['response']:
        send_sms(from_number, result['response'])

    return Response(str(resp), mimetype='application/xml')


# ============================================
# VOICE MESSAGE HANDLING
# ============================================

@app.route('/voice', methods=['POST'])
def handle_voice():
    """
    Handle incoming voice calls - prompt user to speak command
    Set this as your Twilio Voice webhook URL
    """
    from_number = request.values.get('From', '')

    # Check authorization
    if not is_authorized(from_number):
        resp = VoiceResponse()
        resp.say("You are not authorized to use this service. Goodbye.")
        resp.hangup()
        return Response(str(resp), mimetype='application/xml')

    resp = VoiceResponse()

    # Greet and gather speech input
    gather = Gather(
        input='speech',
        action='/voice/process',
        method='POST',
        language='en-AU',
        speech_timeout='auto',
        timeout=5
    )
    gather.say(
        "Voice agent trigger. Say your command. "
        "For example: Call John at 0 4 0 0 1 2 3 4 5 6 about the Inner West property.",
        voice='Polly.Nicole'
    )

    resp.append(gather)

    # If no input, prompt again
    resp.say("I didn't hear anything. Please try again.")
    resp.redirect('/voice')

    return Response(str(resp), mimetype='application/xml')


@app.route('/voice/process', methods=['POST'])
def process_voice():
    """Process the transcribed voice command"""
    from_number = request.values.get('From', '')
    speech_result = request.values.get('SpeechResult', '')

    resp = VoiceResponse()

    if not speech_result:
        resp.say("I couldn't understand that. Please try again.")
        resp.redirect('/voice')
        return Response(str(resp), mimetype='application/xml')

    # Process the voice command
    result = process_command(speech_result, from_number, source='voice')

    # Speak the result
    resp.say(result['response'], voice='Polly.Nicole')

    if result['success'] and 'Call initiated' in result['response']:
        resp.say("The call is being placed now. You will receive an SMS confirmation.")
        # Send SMS confirmation
        try:
            send_sms(from_number, f"Voice command received: {result['response']}")
        except:
            pass

    # Ask if they want to make another call
    gather = Gather(
        input='speech',
        action='/voice/process',
        method='POST',
        language='en-AU',
        speech_timeout='auto',
        timeout=3
    )
    gather.say("Say another command, or hang up to end.", voice='Polly.Nicole')
    resp.append(gather)

    resp.say("Goodbye.")
    resp.hangup()

    return Response(str(resp), mimetype='application/xml')


@app.route('/voice/recording', methods=['POST'])
def handle_voice_recording():
    """
    Alternative: Handle voicemail-style recordings with transcription
    Configure Twilio to record and transcribe, then POST here
    """
    from_number = request.values.get('From', '')
    transcription = request.values.get('TranscriptionText', '')
    recording_url = request.values.get('RecordingUrl', '')

    if not transcription:
        return '', 200

    # Check authorization
    if not is_authorized(from_number):
        return '', 200

    # Process the transcribed voicemail
    result = process_command(transcription, from_number, source='voicemail')

    # Send SMS with result
    try:
        send_sms(
            from_number,
            f"Voicemail processed:\n\"{transcription[:100]}...\"\n\nResult: {result['response']}"
        )
    except:
        pass

    return '', 200


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
