"""
API endpoint for form submission.
Persists buyer briefs to Mem0 for integration with voice agents.
"""

import os
import json
import requests
from datetime import datetime
from http.server import BaseHTTPRequestHandler


# Mem0 configuration
MEM0_API_KEY = os.getenv('MEM0_API_KEY', '')
MEM0_BASE_URL = "https://api.mem0.ai/v1"


def add_to_mem0(phone: str, brief_data: dict) -> dict:
    """Store brief in Mem0 for voice agent integration"""
    if not MEM0_API_KEY:
        return {'success': False, 'error': 'Mem0 not configured'}

    # Normalize phone number
    user_id = ''.join(c for c in phone if c.isdigit() or c == '+')

    # Create a structured message for the memory
    message = f"""New buyer brief submitted:
- Name: {brief_data.get('fullName', 'Unknown')}
- Email: {brief_data.get('email', 'N/A')}
- Purpose: {brief_data.get('purchasePurpose', 'N/A')}
- Budget: ${brief_data.get('budgetMin', 'N/A')} - ${brief_data.get('budgetMax', 'N/A')}
- Preferred areas: {brief_data.get('preferredSuburbs', 'N/A')}
- Property type: {brief_data.get('propertyType', 'N/A')}
- Bedrooms: {brief_data.get('bedrooms', 'N/A')}, Bathrooms: {brief_data.get('bathrooms', 'N/A')}
- Timeline: {brief_data.get('timeline', 'N/A')}
- First home buyer: {brief_data.get('firstHomeBuyer', 'No')}
- Finance status: {brief_data.get('financeStatus', 'N/A')}
- Deal breakers: {brief_data.get('dealBreakers', 'N/A')}
- Additional notes: {brief_data.get('additionalNotes', 'N/A')}"""

    headers = {
        "Authorization": f"Token {MEM0_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "messages": [{"role": "user", "content": message}],
        "user_id": user_id,
        "metadata": {
            "type": "buyer_brief",
            "source": "website_form",
            "timestamp": datetime.now().isoformat(),
            "raw_data": json.dumps(brief_data)
        }
    }

    try:
        response = requests.post(
            f"{MEM0_BASE_URL}/memories/",
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code in [200, 201]:
            return {'success': True, 'data': response.json()}
        else:
            return {'success': False, 'error': f'API error: {response.status_code}'}

    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': str(e)}


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        """Handle form submission"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))

            # Validate required fields
            required_fields = ['fullName', 'email', 'phone']
            missing = [f for f in required_fields if not data.get(f)]

            if missing:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': f'Missing required fields: {", ".join(missing)}'
                }).encode())
                return

            # Add timestamp
            data['submittedAt'] = datetime.now().isoformat()

            # Store in Mem0
            result = add_to_mem0(data['phone'], data)

            if result['success']:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'message': 'Brief submitted successfully',
                    'briefId': data['submittedAt']
                }).encode())
            else:
                # Still return success to user but log the error
                print(f"Mem0 error: {result.get('error')}")
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'message': 'Brief submitted successfully',
                    'briefId': data['submittedAt']
                }).encode())

        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'error': 'Invalid JSON'
            }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'error': str(e)
            }).encode())
