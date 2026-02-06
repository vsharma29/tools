"""
ElevenLabs Outbound Caller
Calls prospects using your ElevenLabs voice agent
"""

import os
import csv
import time
import requests
from datetime import datetime
from typing import List, Dict

# Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")  # Your agent ID from ElevenLabs
AGENT_PHONE_NUMBER = os.getenv("AGENT_PHONE_NUMBER")  # Twilio number linked to agent

# ElevenLabs API base URL
BASE_URL = "https://api.elevenlabs.io/v1"


def load_prospects(csv_file: str) -> List[Dict]:
    """Load prospects from CSV file"""
    prospects = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            prospects.append({
                'name': row.get('name', ''),
                'phone': row.get('phone', ''),
                'email': row.get('email', ''),
                'context': row.get('context', ''),  # Custom context for the call
                'status': 'pending'
            })
    return prospects


def initiate_call(prospect: Dict) -> Dict:
    """
    Initiate an outbound call to a prospect using ElevenLabs agent

    Uses the ElevenLabs Conversational AI outbound call API
    """

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    # Prepare dynamic variables for the agent
    # These can be used in your agent's prompts like {{name}}, {{context}}
    first_message = f"Hi, is this {prospect['name']}?"

    payload = {
        "agent_id": AGENT_ID,
        "agent_phone_number": AGENT_PHONE_NUMBER,
        "customer_phone_number": prospect['phone'],
        "first_message": first_message,
        # Dynamic variables passed to agent prompt
        "dynamic_variables": {
            "prospect_name": prospect['name'],
            "prospect_context": prospect.get('context', ''),
        }
    }

    try:
        response = requests.post(
            f"{BASE_URL}/convai/conversations/call",
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            result = response.json()
            return {
                'success': True,
                'conversation_id': result.get('conversation_id'),
                'call_sid': result.get('call_sid'),
                'prospect': prospect['name']
            }
        else:
            return {
                'success': False,
                'error': response.text,
                'prospect': prospect['name']
            }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'prospect': prospect['name']
        }


def run_campaign(prospects: List[Dict], delay_between_calls: int = 30):
    """
    Run outbound calling campaign

    Args:
        prospects: List of prospect dictionaries
        delay_between_calls: Seconds to wait between calls (default 30)
    """

    print(f"\n{'='*50}")
    print(f"OUTBOUND CALLING CAMPAIGN")
    print(f"{'='*50}")
    print(f"Total prospects: {len(prospects)}")
    print(f"Delay between calls: {delay_between_calls}s")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    results = []

    for i, prospect in enumerate(prospects, 1):
        print(f"\n[{i}/{len(prospects)}] Calling {prospect['name']} at {prospect['phone']}...")

        result = initiate_call(prospect)
        results.append(result)

        if result['success']:
            print(f"  ✓ Call initiated - Conversation ID: {result['conversation_id']}")
        else:
            print(f"  ✗ Failed: {result['error']}")

        # Wait before next call (unless it's the last one)
        if i < len(prospects):
            print(f"  Waiting {delay_between_calls}s before next call...")
            time.sleep(delay_between_calls)

    # Summary
    successful = sum(1 for r in results if r['success'])
    print(f"\n{'='*50}")
    print(f"CAMPAIGN COMPLETE")
    print(f"{'='*50}")
    print(f"Successful calls: {successful}/{len(prospects)}")
    print(f"Failed calls: {len(prospects) - successful}/{len(prospects)}")
    print(f"{'='*50}\n")

    return results


def get_call_results(conversation_id: str) -> Dict:
    """Get results/transcript of a completed call"""

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY
    }

    response = requests.get(
        f"{BASE_URL}/convai/conversations/{conversation_id}",
        headers=headers
    )

    if response.status_code == 200:
        return response.json()
    return None


# Example usage
if __name__ == "__main__":
    # Example: Load from CSV
    # prospects = load_prospects("prospects.csv")

    # Or define prospects directly
    prospects = [
        {
            "name": "John Smith",
            "phone": "+61400000001",
            "context": "Interested in properties in Sydney Inner West"
        },
        {
            "name": "Sarah Johnson",
            "phone": "+61400000002",
            "context": "First home buyer looking for apartments"
        },
        # Add more prospects...
    ]

    # Run the campaign
    # results = run_campaign(prospects, delay_between_calls=60)

    print("To run the campaign, uncomment the run_campaign line above")
    print("\nMake sure you have set these environment variables:")
    print("  - ELEVENLABS_API_KEY")
    print("  - ELEVENLABS_AGENT_ID")
    print("  - AGENT_PHONE_NUMBER")
