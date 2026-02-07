#!/usr/bin/env python3
"""
Twilio Configuration Script for ElevenLabs Voice Agent

This script configures your Twilio phone number webhooks programmatically.

Prerequisites:
    1. Twilio account with a phone number purchased
    2. ElevenLabs agent created
    3. Twilio connected to ElevenLabs via Phone Numbers section

Usage:
    python configure_twilio.py --setup          # Interactive setup
    python configure_twilio.py --status         # Check current config
    python configure_twilio.py --update-webhooks # Update webhook URLs

Environment Variables (or use .env file):
    TWILIO_ACCOUNT_SID
    TWILIO_AUTH_TOKEN
    TWILIO_PHONE_NUMBER
    ELEVENLABS_AGENT_ID
"""

import os
import sys
import argparse
import requests
from urllib.parse import urlencode

# Try to load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class TwilioConfig:
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        self.agent_id = os.getenv('ELEVENLABS_AGENT_ID')

        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"

    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make authenticated request to Twilio API"""
        url = f"{self.base_url}{endpoint}"
        auth = (self.account_sid, self.auth_token)

        if method == 'GET':
            response = requests.get(url, auth=auth)
        elif method == 'POST':
            response = requests.post(url, auth=auth, data=data)
        else:
            raise ValueError(f"Unsupported method: {method}")

        return response.json()

    def get_phone_number_sid(self) -> str:
        """Get the SID for the configured phone number"""
        # Normalize phone number
        phone = self.phone_number
        if not phone.startswith('+'):
            phone = f"+{phone}"

        result = self._request('GET', f"/IncomingPhoneNumbers.json?PhoneNumber={phone}")

        numbers = result.get('incoming_phone_numbers', [])
        if not numbers:
            print(f"Error: Phone number {phone} not found in your Twilio account")
            return None

        return numbers[0]['sid']

    def get_current_config(self) -> dict:
        """Get current webhook configuration for the phone number"""
        phone_sid = self.get_phone_number_sid()
        if not phone_sid:
            return None

        result = self._request('GET', f"/IncomingPhoneNumbers/{phone_sid}.json")

        return {
            'phone_number': result.get('phone_number'),
            'friendly_name': result.get('friendly_name'),
            'voice_url': result.get('voice_url'),
            'voice_method': result.get('voice_method'),
            'sms_url': result.get('sms_url'),
            'sms_method': result.get('sms_method'),
            'status_callback': result.get('status_callback'),
            'capabilities': result.get('capabilities'),
        }

    def update_webhooks(self, voice_url: str = None, sms_url: str = None,
                        status_callback: str = None) -> dict:
        """Update webhook URLs for the phone number"""
        phone_sid = self.get_phone_number_sid()
        if not phone_sid:
            return None

        data = {}
        if voice_url:
            data['VoiceUrl'] = voice_url
            data['VoiceMethod'] = 'POST'
        if sms_url:
            data['SmsUrl'] = sms_url
            data['SmsMethod'] = 'POST'
        if status_callback:
            data['StatusCallback'] = status_callback
            data['StatusCallbackMethod'] = 'POST'

        result = self._request('POST', f"/IncomingPhoneNumbers/{phone_sid}.json", data)

        return {
            'voice_url': result.get('voice_url'),
            'sms_url': result.get('sms_url'),
            'status_callback': result.get('status_callback'),
        }

    def get_recent_calls(self, limit: int = 5) -> list:
        """Get recent call logs"""
        result = self._request('GET', f"/Calls.json?PageSize={limit}")

        calls = []
        for call in result.get('calls', []):
            calls.append({
                'sid': call.get('sid'),
                'from': call.get('from_formatted'),
                'to': call.get('to_formatted'),
                'status': call.get('status'),
                'direction': call.get('direction'),
                'duration': call.get('duration'),
                'date': call.get('date_created'),
            })

        return calls

    def get_call_errors(self, call_sid: str) -> list:
        """Get errors/notifications for a specific call"""
        result = self._request('GET', f"/Calls/{call_sid}/Notifications.json")

        errors = []
        for notif in result.get('notifications', []):
            errors.append({
                'error_code': notif.get('error_code'),
                'message': notif.get('message_text'),
                'more_info': notif.get('more_info'),
                'date': notif.get('date_created'),
            })

        return errors


def print_config(config: dict):
    """Pretty print configuration"""
    print("\n" + "=" * 50)
    print("CURRENT TWILIO CONFIGURATION")
    print("=" * 50)
    for key, value in config.items():
        print(f"  {key}: {value}")
    print("=" * 50 + "\n")


def print_calls(calls: list):
    """Pretty print call logs"""
    print("\n" + "=" * 50)
    print("RECENT CALLS")
    print("=" * 50)
    for call in calls:
        status_icon = "✓" if call['status'] == 'completed' else "✗"
        print(f"  {status_icon} {call['date']}")
        print(f"    {call['from']} → {call['to']}")
        print(f"    Status: {call['status']}, Duration: {call['duration']}s")
        print(f"    SID: {call['sid']}")
        print()
    print("=" * 50 + "\n")


def interactive_setup():
    """Interactive setup wizard"""
    print("\n" + "=" * 50)
    print("TWILIO + ELEVENLABS SETUP WIZARD")
    print("=" * 50 + "\n")

    # Collect credentials
    account_sid = input("Twilio Account SID: ").strip()
    auth_token = input("Twilio Auth Token: ").strip()
    phone_number = input("Twilio Phone Number (e.g., +61485027700): ").strip()
    agent_id = input("ElevenLabs Agent ID: ").strip()

    # Set environment variables for this session
    os.environ['TWILIO_ACCOUNT_SID'] = account_sid
    os.environ['TWILIO_AUTH_TOKEN'] = auth_token
    os.environ['TWILIO_PHONE_NUMBER'] = phone_number
    os.environ['ELEVENLABS_AGENT_ID'] = agent_id

    config = TwilioConfig()

    # Show current config
    current = config.get_current_config()
    if current:
        print_config(current)

    # Ask about webhook setup
    print("\nWebhook Configuration Options:")
    print("  1. ElevenLabs Inbound (voice) + SMS Trigger")
    print("  2. SMS Trigger only")
    print("  3. Custom URLs")
    print("  4. Skip webhook setup")

    choice = input("\nSelect option (1-4): ").strip()

    sms_trigger_url = input("SMS Trigger URL (e.g., https://smstrigger.vercel.app/sms): ").strip()

    if choice == '1':
        voice_url = f"https://api.elevenlabs.io/v1/convai/twilio/inbound_call?agent_id={agent_id}"
        result = config.update_webhooks(voice_url=voice_url, sms_url=sms_trigger_url)
    elif choice == '2':
        result = config.update_webhooks(sms_url=sms_trigger_url)
    elif choice == '3':
        voice_url = input("Voice webhook URL: ").strip()
        result = config.update_webhooks(voice_url=voice_url, sms_url=sms_trigger_url)
    else:
        result = None

    if result:
        print("\n✓ Webhooks updated successfully!")
        print(f"  Voice URL: {result.get('voice_url')}")
        print(f"  SMS URL: {result.get('sms_url')}")

    # Generate .env file
    print("\n" + "-" * 50)
    env_content = f"""# Twilio Configuration
TWILIO_ACCOUNT_SID={account_sid}
TWILIO_AUTH_TOKEN={auth_token}
TWILIO_PHONE_NUMBER={phone_number}

# ElevenLabs Configuration
ELEVENLABS_AGENT_ID={agent_id}
ELEVENLABS_API_KEY=your_api_key_here

# Optional: Authorized numbers for SMS trigger (comma-separated)
AUTHORIZED_NUMBERS=
"""

    save_env = input("Save to .env file? (y/n): ").strip().lower()
    if save_env == 'y':
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✓ Saved to .env")
    else:
        print("\n.env content (copy this):")
        print(env_content)

    print("\n✓ Setup complete!\n")


def main():
    parser = argparse.ArgumentParser(description='Configure Twilio for ElevenLabs Voice Agent')
    parser.add_argument('--setup', action='store_true', help='Interactive setup wizard')
    parser.add_argument('--status', action='store_true', help='Show current configuration')
    parser.add_argument('--calls', action='store_true', help='Show recent call logs')
    parser.add_argument('--errors', type=str, help='Show errors for a call SID')
    parser.add_argument('--update-webhooks', action='store_true', help='Update webhook URLs')
    parser.add_argument('--voice-url', type=str, help='Voice webhook URL')
    parser.add_argument('--sms-url', type=str, help='SMS webhook URL')

    args = parser.parse_args()

    if args.setup:
        interactive_setup()
        return

    # Validate environment
    required = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER']
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        print("Run with --setup for interactive configuration")
        sys.exit(1)

    config = TwilioConfig()

    if args.status:
        current = config.get_current_config()
        if current:
            print_config(current)

    elif args.calls:
        calls = config.get_recent_calls()
        print_calls(calls)

    elif args.errors:
        errors = config.get_call_errors(args.errors)
        if errors:
            print(f"\nErrors for call {args.errors}:")
            for err in errors:
                print(f"  Code: {err['error_code']}")
                print(f"  Info: {err['more_info']}")
                print()
        else:
            print("No errors found for this call")

    elif args.update_webhooks:
        result = config.update_webhooks(
            voice_url=args.voice_url,
            sms_url=args.sms_url
        )
        if result:
            print("✓ Webhooks updated:")
            print(f"  Voice: {result.get('voice_url')}")
            print(f"  SMS: {result.get('sms_url')}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
