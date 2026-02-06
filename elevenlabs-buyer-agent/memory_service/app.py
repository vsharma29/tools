"""
Memory Service for ElevenLabs Voice Agent
Webhook handler that connects ElevenLabs tool calls to Mem0 for persistent memory

Uses caller phone number as unique identifier for memory storage/retrieval.

ElevenLabs Agent Tools:
    - retrieveMemories: Get past interactions with this caller
    - addMemories: Store important information for future calls
"""

import os
import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Mem0 Configuration
MEM0_API_KEY = os.getenv('MEM0_API_KEY')
MEM0_API_URL = "https://api.mem0.ai/v1"

# Optional: Organization/Project ID for Mem0
MEM0_ORG_ID = os.getenv('MEM0_ORG_ID', '')
MEM0_PROJECT_ID = os.getenv('MEM0_PROJECT_ID', '')


def normalize_phone(phone: str) -> str:
    """Normalize phone number to use as user_id"""
    # Remove spaces, dashes, parentheses
    normalized = ''.join(c for c in phone if c.isdigit() or c == '+')
    return normalized


def mem0_add_memory(user_id: str, message: str, metadata: dict = None) -> dict:
    """
    Add a memory to Mem0 for a specific user

    Args:
        user_id: Phone number as unique identifier
        message: The information to remember
        metadata: Optional metadata (call_id, timestamp, etc.)
    """
    headers = {
        "Authorization": f"Token {MEM0_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "messages": [
            {
                "role": "user",
                "content": message
            }
        ],
        "user_id": user_id,
        "metadata": metadata or {}
    }

    # Add org/project if configured
    if MEM0_ORG_ID:
        payload["org_id"] = MEM0_ORG_ID
    if MEM0_PROJECT_ID:
        payload["project_id"] = MEM0_PROJECT_ID

    try:
        response = requests.post(
            f"{MEM0_API_URL}/memories/",
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code in [200, 201]:
            return {
                "success": True,
                "data": response.json()
            }
        else:
            return {
                "success": False,
                "error": f"Mem0 API error: {response.status_code} - {response.text}"
            }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e)
        }


def mem0_search_memories(user_id: str, query: str, limit: int = 10) -> dict:
    """
    Search memories for a specific user

    Args:
        user_id: Phone number as unique identifier
        query: Search query for semantic matching
        limit: Max number of memories to return
    """
    headers = {
        "Authorization": f"Token {MEM0_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,
        "user_id": user_id,
        "limit": limit
    }

    if MEM0_ORG_ID:
        payload["org_id"] = MEM0_ORG_ID
    if MEM0_PROJECT_ID:
        payload["project_id"] = MEM0_PROJECT_ID

    try:
        response = requests.post(
            f"{MEM0_API_URL}/memories/search/",
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "memories": data.get("results", [])
            }
        else:
            return {
                "success": False,
                "error": f"Mem0 API error: {response.status_code}",
                "memories": []
            }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "memories": []
        }


def mem0_get_all_memories(user_id: str) -> dict:
    """Get all memories for a user"""
    headers = {
        "Authorization": f"Token {MEM0_API_KEY}",
        "Content-Type": "application/json"
    }

    params = {"user_id": user_id}

    if MEM0_ORG_ID:
        params["org_id"] = MEM0_ORG_ID
    if MEM0_PROJECT_ID:
        params["project_id"] = MEM0_PROJECT_ID

    try:
        response = requests.get(
            f"{MEM0_API_URL}/memories/",
            headers=headers,
            params=params,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "memories": data.get("results", data) if isinstance(data, dict) else data
            }
        else:
            return {
                "success": False,
                "memories": []
            }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "memories": []
        }


# ============================================
# ELEVENLABS WEBHOOK ENDPOINTS
# ============================================

@app.route('/')
def index():
    """Landing page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Memory Service - Voice Agent</title>
        <style>
            body { font-family: system-ui, sans-serif; max-width: 700px; margin: 50px auto; padding: 20px; background: #000; color: #fff; }
            h1 { border-bottom: 2px solid #fff; padding-bottom: 10px; }
            h2 { margin-top: 30px; color: #aaa; }
            code { background: #222; padding: 2px 8px; border-radius: 4px; font-size: 14px; }
            pre { background: #111; padding: 15px; border-radius: 8px; overflow-x: auto; }
            .endpoint { background: #0a0a0a; padding: 20px; border-radius: 12px; margin: 20px 0; }
            .method { display: inline-block; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; }
            .post { background: #1a4; }
            .get { background: #14a; }
            .status { color: #0f0; }
        </style>
    </head>
    <body>
        <h1>Memory Service</h1>
        <p class="status">Status: Active</p>
        <p>Persistent memory for ElevenLabs Voice Agent using Mem0</p>

        <h2>ElevenLabs Tool Webhooks</h2>

        <div class="endpoint">
            <p><span class="method post">POST</span> <code>/tools/retrieveMemories</code></p>
            <p>Retrieve past interactions with a caller</p>
            <pre>{
  "phone": "+61400123456",
  "query": "property preferences"
}</pre>
        </div>

        <div class="endpoint">
            <p><span class="method post">POST</span> <code>/tools/addMemories</code></p>
            <p>Store information for future calls</p>
            <pre>{
  "phone": "+61400123456",
  "message": "Interested in 3-bed house, budget $1.5M"
}</pre>
        </div>

        <h2>Admin Endpoints</h2>

        <div class="endpoint">
            <p><span class="method get">GET</span> <code>/memories/&lt;phone&gt;</code></p>
            <p>View all memories for a phone number</p>
        </div>

        <h2>ElevenLabs Setup</h2>
        <p>Add these tools to your agent with webhook URLs pointing to this service.</p>
    </body>
    </html>
    """


@app.route('/tools/retrieveMemories', methods=['POST'])
def retrieve_memories():
    """
    ElevenLabs tool webhook: Retrieve memories for a caller

    Expected payload from ElevenLabs:
    {
        "phone": "+61400123456",  // or passed via dynamic variables
        "query": "what properties are they interested in"
    }
    """
    data = request.json or {}

    # Get phone number - could come from various places in ElevenLabs payload
    phone = (
        data.get('phone') or
        data.get('customer_phone_number') or
        data.get('parameters', {}).get('phone') or
        data.get('dynamic_variables', {}).get('customer_phone') or
        ''
    )

    query = (
        data.get('query') or
        data.get('message') or
        data.get('parameters', {}).get('query') or
        'past conversations and preferences'
    )

    if not phone:
        return jsonify({
            "success": False,
            "error": "No phone number provided",
            "result": "I don't have access to your previous conversations yet."
        }), 400

    user_id = normalize_phone(phone)

    # Search for relevant memories
    result = mem0_search_memories(user_id, query, limit=5)

    if result['success'] and result['memories']:
        # Format memories for the agent
        memory_texts = []
        for mem in result['memories']:
            content = mem.get('memory', mem.get('content', ''))
            if content:
                memory_texts.append(f"- {content}")

        if memory_texts:
            formatted = "Previous interactions with this caller:\n" + "\n".join(memory_texts)
        else:
            formatted = "No specific memories found for this query."
    else:
        formatted = "This is a new caller with no previous interaction history."

    return jsonify({
        "success": True,
        "result": formatted,
        "memories": result.get('memories', []),
        "user_id": user_id
    })


@app.route('/tools/addMemories', methods=['POST'])
def add_memories():
    """
    ElevenLabs tool webhook: Store memory for a caller

    Expected payload:
    {
        "phone": "+61400123456",
        "message": "Customer interested in Inner West, budget $1.2M, needs 3 bedrooms"
    }
    """
    data = request.json or {}

    phone = (
        data.get('phone') or
        data.get('customer_phone_number') or
        data.get('parameters', {}).get('phone') or
        data.get('dynamic_variables', {}).get('customer_phone') or
        ''
    )

    message = (
        data.get('message') or
        data.get('content') or
        data.get('parameters', {}).get('message') or
        ''
    )

    if not phone:
        return jsonify({
            "success": False,
            "error": "No phone number provided",
            "result": "Could not save memory - no phone number."
        }), 400

    if not message:
        return jsonify({
            "success": False,
            "error": "No message provided",
            "result": "Could not save memory - no content."
        }), 400

    user_id = normalize_phone(phone)

    # Add metadata
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "source": "voice_agent",
        "call_id": data.get('conversation_id', ''),
    }

    result = mem0_add_memory(user_id, message, metadata)

    if result['success']:
        return jsonify({
            "success": True,
            "result": "Information saved for future reference.",
            "user_id": user_id
        })
    else:
        return jsonify({
            "success": False,
            "result": "Could not save memory at this time.",
            "error": result.get('error', 'Unknown error')
        }), 500


# ============================================
# ADMIN/DEBUG ENDPOINTS
# ============================================

@app.route('/memories/<phone>', methods=['GET'])
def get_memories(phone):
    """Get all memories for a phone number (admin endpoint)"""
    user_id = normalize_phone(phone)
    result = mem0_get_all_memories(user_id)

    return jsonify({
        "phone": phone,
        "user_id": user_id,
        "memories": result.get('memories', []),
        "success": result['success']
    })


@app.route('/memories/<phone>/search', methods=['POST'])
def search_memories(phone):
    """Search memories for a phone number"""
    data = request.json or {}
    query = data.get('query', 'all information')

    user_id = normalize_phone(phone)
    result = mem0_search_memories(user_id, query)

    return jsonify({
        "phone": phone,
        "user_id": user_id,
        "query": query,
        "memories": result.get('memories', []),
        "success": result['success']
    })


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'memory-service',
        'mem0_configured': bool(MEM0_API_KEY),
        'timestamp': datetime.now().isoformat()
    })


# ============================================
# ELEVENLABS CONVERSATION HOOKS
# ============================================

@app.route('/hooks/conversation-start', methods=['POST'])
def conversation_start_hook():
    """
    Hook called at the start of an ElevenLabs conversation
    Returns context to inject into the conversation
    """
    data = request.json or {}

    phone = (
        data.get('customer_phone_number') or
        data.get('phone') or
        ''
    )

    if not phone:
        return jsonify({
            "context": "",
            "dynamic_variables": {}
        })

    user_id = normalize_phone(phone)

    # Get recent memories
    result = mem0_search_memories(user_id, "recent interactions preferences interests", limit=3)

    context = ""
    if result['success'] and result['memories']:
        memory_texts = [m.get('memory', '') for m in result['memories'] if m.get('memory')]
        if memory_texts:
            context = f"CALLER HISTORY ({phone}):\n" + "\n".join(f"- {m}" for m in memory_texts)

    return jsonify({
        "context": context,
        "has_history": bool(context),
        "dynamic_variables": {
            "caller_history": context,
            "is_returning_caller": bool(context)
        }
    })


@app.route('/hooks/conversation-end', methods=['POST'])
def conversation_end_hook():
    """
    Hook called at the end of an ElevenLabs conversation
    Can be used to auto-save conversation summary
    """
    data = request.json or {}

    phone = data.get('customer_phone_number', '')
    summary = data.get('conversation_summary', '')

    if phone and summary:
        user_id = normalize_phone(phone)
        mem0_add_memory(user_id, f"Call summary: {summary}", {
            "type": "conversation_summary",
            "timestamp": datetime.now().isoformat()
        })

    return jsonify({"success": True})


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)
