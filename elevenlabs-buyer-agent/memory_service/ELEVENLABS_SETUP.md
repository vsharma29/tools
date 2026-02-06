# ElevenLabs Memory Integration Setup

## 1. Add Tools to Your Agent

Go to your ElevenLabs agent → **Tools** → Add these two webhook tools:

### Tool 1: retrieveMemories

```json
{
  "name": "retrieveMemories",
  "description": "Retrieve relevant information from past conversations with this caller. Use this at the START of every call to check for previous interactions.",
  "webhook_url": "https://YOUR_MEMORY_SERVICE.vercel.app/tools/retrieveMemories",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "What to search for in past memories (e.g., 'property preferences', 'budget', 'previous discussions')"
      }
    },
    "required": ["query"]
  }
}
```

### Tool 2: addMemories

```json
{
  "name": "addMemories",
  "description": "Store important information from this conversation for future calls. Use this when the caller shares preferences, requirements, or important details.",
  "webhook_url": "https://YOUR_MEMORY_SERVICE.vercel.app/tools/addMemories",
  "parameters": {
    "type": "object",
    "properties": {
      "message": {
        "type": "string",
        "description": "The important information to remember (e.g., 'Interested in 3-bedroom house in Inner West, budget $1.5M, needs parking')"
      }
    },
    "required": ["message"]
  }
}
```

## 2. Update Agent System Prompt

Add this to your agent's system prompt:

```
## Memory Instructions

At the START of every call:
1. Call retrieveMemories with query "previous interactions and preferences"
2. If memories exist, acknowledge the caller and reference relevant past information
3. If no memories, treat as a new caller

During the conversation:
- When the caller shares important information (budget, preferences, timeline, property requirements), call addMemories to save it
- Information worth saving includes:
  - Property preferences (bedrooms, location, features)
  - Budget and financing status
  - Timeline for purchase
  - Specific properties discussed
  - Personal details shared (family size, work location)
  - Action items or follow-ups promised

Example addMemories calls:
- "Budget is $1.2-1.5M, looking for 3-bed house in Inner West"
- "Pre-approved with ANZ, ready to buy within 3 months"
- "Interested in 45 Smith St, wants to schedule inspection"
```

## 3. Pass Phone Number to Tools

In your ElevenLabs agent configuration, ensure the customer phone number is passed to webhook tools.

Under **Conversation Settings** → **Dynamic Variables**, add:
- `customer_phone` → `{{customer_phone_number}}`

Then update your webhook tools to include:
```json
{
  "headers": {
    "X-Customer-Phone": "{{customer_phone_number}}"
  }
}
```

Or include in the request body via the conversation_initiation_client_data when making outbound calls.

## 4. Environment Variables for Memory Service

Set these in Vercel:
- `MEM0_API_KEY` - Your Mem0 API key (get from https://app.mem0.ai)
- `MEM0_ORG_ID` - (Optional) Your Mem0 organization ID
- `MEM0_PROJECT_ID` - (Optional) Your Mem0 project ID

## 5. Test the Integration

1. Make a test call to your agent
2. Share some information ("I'm looking for a 3-bed house in Bondi, budget around $2M")
3. End the call
4. Call again - the agent should remember your preferences

## Webhook Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tools/retrieveMemories` | POST | Search caller's memories |
| `/tools/addMemories` | POST | Store new memory |
| `/memories/<phone>` | GET | Admin: view all memories |
| `/hooks/conversation-start` | POST | Auto-inject context at call start |
| `/hooks/conversation-end` | POST | Auto-save conversation summary |

## Example Payloads

### retrieveMemories Request
```json
{
  "phone": "+61400123456",
  "query": "property preferences and budget"
}
```

### retrieveMemories Response
```json
{
  "success": true,
  "result": "Previous interactions with this caller:\n- Budget is $1.5M, looking for Inner West\n- Interested in 3-bedroom houses with parking",
  "memories": [...]
}
```

### addMemories Request
```json
{
  "phone": "+61400123456",
  "message": "Wants to schedule inspection for 45 Smith St Marrickville this Saturday"
}
```
