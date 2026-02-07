"""
API endpoint to retrieve buyer briefs.
Fetches briefs from Mem0 by phone number.
"""

import os
import json
import requests
from urllib.parse import parse_qs
from http.server import BaseHTTPRequestHandler


# Mem0 configuration
MEM0_API_KEY = os.getenv('MEM0_API_KEY', '')
MEM0_BASE_URL = "https://api.mem0.ai/v1"


def get_briefs(phone: str) -> list:
    """Get all briefs for a phone number from Mem0"""
    if not MEM0_API_KEY:
        return []

    # Normalize phone number
    user_id = ''.join(c for c in phone if c.isdigit() or c == '+')

    headers = {
        "Authorization": f"Token {MEM0_API_KEY}",
        "Content-Type": "application/json"
    }

    params = {"user_id": user_id}

    try:
        response = requests.get(
            f"{MEM0_BASE_URL}/memories/",
            headers=headers,
            params=params,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            memories = data.get('results', data) if isinstance(data, dict) else data

            # Filter for buyer briefs only
            briefs = []
            for memory in memories:
                metadata = memory.get('metadata', {})
                if metadata.get('type') == 'buyer_brief':
                    raw_data = metadata.get('raw_data')
                    if raw_data:
                        try:
                            brief_data = json.loads(raw_data)
                            briefs.append({
                                'id': memory.get('id'),
                                'submittedAt': metadata.get('timestamp'),
                                'data': brief_data
                            })
                        except json.JSONDecodeError:
                            pass

            return briefs
        return []

    except requests.exceptions.RequestException:
        return []


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """Handle brief retrieval"""
        try:
            # Parse query parameters
            query = self.path.split('?')[1] if '?' in self.path else ''
            params = parse_qs(query)
            phone = params.get('phone', [''])[0]

            if not phone:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': 'Phone number required'
                }).encode())
                return

            briefs = get_briefs(phone)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'briefs': briefs
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
