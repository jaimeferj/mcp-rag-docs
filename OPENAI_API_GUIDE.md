# OpenAI-Compatible API Guide

## Overview

The RAG system now provides an OpenAI-compatible API that allows integration with web UIs like **Open WebUI** and **LibreChat**. This enables you to interact with your indexed documentation and code through familiar chat interfaces.

## Features

✅ **OpenAI-Compatible Endpoints** - `/v1/chat/completions`, `/v1/models`
✅ **Streaming Support** - Real-time response streaming
✅ **Multiple Models** - Choose between smart, standard, and enhanced RAG
✅ **Custom Parameters** - Control detail level, repository filtering, and more
✅ **CORS Enabled** - Works with web UIs out of the box

## Available Models

### `rag-smart` (Recommended)
- **Description:** Intelligent query routing with automatic classification
- **Best for:** General questions, automatic optimal tool selection
- **Features:** Query classification, confidence scoring, reasoning trace
- **Speed:** Fast (code index) or moderate (depending on query type)

### `rag-standard`
- **Description:** Standard RAG query with documentation search
- **Best for:** Documentation-focused questions
- **Features:** Semantic search through docs
- **Speed:** Moderate

### `rag-enhanced`
- **Description:** Enhanced RAG with automatic reference following
- **Best for:** Complex questions requiring multiple steps
- **Features:** Auto-follows references, retrieves source code
- **Speed:** Slower but comprehensive

## Quick Start

### 1. Start the Server

```bash
# Make sure the server is running
python -m rag_server.server
```

The server will start at `http://localhost:8000` with:
- Custom API: `http://localhost:8000`
- OpenAI API: `http://localhost:8000/v1`

### 2. Verify It's Working

```bash
# List available models
curl http://localhost:8000/v1/models

# Test chat completion
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "rag-smart",
    "messages": [{"role": "user", "content": "show me AutomationCondition.eager"}]
  }'
```

## Integration Guides

### Open WebUI

**Open WebUI** is a modern web interface for LLMs.

#### Installation

```bash
# Using Docker
docker run -d -p 3000:8080 \
  -e OPENAI_API_BASE_URL=http://host.docker.internal:8000/v1 \
  -e OPENAI_API_KEY=optional \
  --name open-webui \
  ghcr.io/open-webui/open-webui:main
```

#### Configuration

1. Open `http://localhost:3000`
2. Go to **Settings** → **Connections**
3. Add OpenAI Connection:
   - **API Base URL:** `http://localhost:8000/v1`
   - **API Key:** Leave empty or use any value
4. Go to **Workspace** → **Models**
5. You should see: `rag-smart`, `rag-standard`, `rag-enhanced`

#### Usage

1. Start a new chat
2. Select `rag-smart` from the model dropdown
3. Ask questions:
   - "show me AutomationCondition.eager"
   - "how do Dagster schedules work"
   - "what methods does AutomationCondition have"

### LibreChat

**LibreChat** is an enhanced ChatGPT clone with multi-provider support.

#### Installation

```bash
# Clone LibreChat
git clone https://github.com/danny-avila/LibreChat.git
cd LibreChat

# Create config file
cp .env.example .env
```

#### Configuration

Edit `librechat.yaml`:

```yaml
version: 1.0.5
cache: true

endpoints:
  custom:
    - name: "RAG System"
      apiKey: "${RAG_API_KEY}"
      baseURL: "http://localhost:8000/v1"
      models:
        default: ["rag-smart", "rag-standard", "rag-enhanced"]
        fetch: false
      titleConvo: true
      titleModel: "rag-smart"
      summarize: false
      summaryModel: "rag-smart"
      forcePrompt: false
      modelDisplayLabel: "RAG System"
```

Edit `.env`:

```bash
RAG_API_KEY=optional
```

#### Start LibreChat

```bash
docker-compose up -d
```

Access at `http://localhost:3080`

### Other OpenAI-Compatible Clients

Any client that supports the OpenAI API can connect:

**Python (OpenAI SDK):**
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="optional"
)

response = client.chat.completions.create(
    model="rag-smart",
    messages=[
        {"role": "user", "content": "show me AutomationCondition.eager"}
    ]
)

print(response.choices[0].message.content)
```

**Node.js:**
```javascript
import OpenAI from 'openai';

const openai = new OpenAI({
  baseURL: 'http://localhost:8000/v1',
  apiKey: 'optional',
});

const completion = await openai.chat.completions.create({
  model: 'rag-smart',
  messages: [
    { role: 'user', content: 'show me AutomationCondition.eager' }
  ],
});

console.log(completion.choices[0].message.content);
```

## Custom Parameters

The RAG system supports additional parameters beyond standard OpenAI:

### `expand_detail`
Get full implementation instead of signatures:
```json
{
  "model": "rag-smart",
  "messages": [{"role": "user", "content": "show me AutomationCondition"}],
  "expand_detail": true
}
```

### `repo_filter`
Filter to specific repository:
```json
{
  "model": "rag-smart",
  "messages": [{"role": "user", "content": "show me Table"}],
  "repo_filter": "dagster"
}
```

### `top_k`
Number of chunks to retrieve:
```json
{
  "model": "rag-standard",
  "messages": [{"role": "user", "content": "how do schedules work"}],
  "top_k": 10
}
```

### `tags`
Filter by document tags:
```json
{
  "model": "rag-standard",
  "messages": [{"role": "user", "content": "deployment guide"}],
  "tags": ["dagster", "deployment"]
}
```

## Streaming

All models support streaming for real-time responses:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "rag-smart",
    "messages": [{"role": "user", "content": "explain schedules"}],
    "stream": true
  }'
```

In web UIs, streaming is automatically enabled for a better user experience.

## System Messages

You can use system messages to provide context or instructions:

```json
{
  "model": "rag-smart",
  "messages": [
    {
      "role": "system",
      "content": "You are a Dagster expert. Provide concise, code-focused answers."
    },
    {
      "role": "user",
      "content": "how do I create a schedule"
    }
  ]
}
```

## Model Selection Guide

### Use `rag-smart` when:
- ✅ You want automatic optimization
- ✅ Asking about specific code ("show me X")
- ✅ General questions
- ✅ You want reasoning traces

### Use `rag-standard` when:
- ✅ Pure documentation questions
- ✅ Conceptual explanations
- ✅ You want faster responses

### Use `rag-enhanced` when:
- ✅ Complex multi-step questions
- ✅ You want automatic reference following
- ✅ How-to questions with examples

## Configuration

### Environment Variables

```bash
# .env file
ENABLE_OPENAI_API=true
OPENAI_API_KEY=optional_key_for_auth
```

### Settings

```python
# config/settings.py
enable_openai_api: bool = True  # Enable/disable OpenAI API
openai_api_key: str = ""        # Optional API key
```

## API Endpoints

### POST `/v1/chat/completions`
Create a chat completion (streaming and non-streaming).

**Request:**
```json
{
  "model": "rag-smart",
  "messages": [
    {"role": "user", "content": "your question"}
  ],
  "stream": false,
  "temperature": 0.7,
  "expand_detail": false,
  "repo_filter": null
}
```

**Response:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "rag-smart",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "The answer..."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 50,
    "total_tokens": 60
  },
  "rag_metadata": {
    "confidence": 0.9,
    "classification": {...}
  }
}
```

### GET `/v1/models`
List available models.

**Response:**
```json
{
  "object": "list",
  "data": [
    {"id": "rag-smart", "object": "model", "created": 1234567890, "owned_by": "rag-system"},
    {"id": "rag-standard", "object": "model", ...},
    {"id": "rag-enhanced", "object": "model", ...}
  ]
}
```

### GET `/v1/models/{model_id}`
Get information about a specific model.

## Troubleshooting

### CORS Errors
If you get CORS errors in the browser:
- The server has CORS enabled for all origins (`*`)
- Check that the server is running
- Verify the web UI is pointing to the correct URL

### Connection Refused
```
Error: connect ECONNREFUSED
```
**Solution:**
- Make sure RAG server is running: `python -m rag_server.server`
- Check the port (default: 8000)
- If using Docker, use `host.docker.internal` instead of `localhost`

### Model Not Found
```
Error: Model 'rag-smart' not found
```
**Solution:**
- Verify models with: `curl http://localhost:8000/v1/models`
- Check `enable_openai_api=true` in settings
- Restart the server

### Empty Responses
If responses are empty:
- Make sure you've indexed documents: `python ingest_docs.py`
- Index code repositories: `python build_code_index.py`
- Check `/stats` endpoint for indexed content

### Slow Responses
- Use `rag-smart` or `rag-standard` instead of `rag-enhanced`
- Reduce `top_k` parameter
- Ensure code index is built for fast code lookups

## Best Practices

### 1. Use Smart Model by Default
```
rag-smart automatically routes to optimal strategy
```

### 2. Provide Context with System Messages
```json
{"role": "system", "content": "Focus on Python examples"}
```

### 3. Enable Streaming for Better UX
```json
{"stream": true}
```

### 4. Filter by Repository for Specific Libraries
```json
{"repo_filter": "dagster"}
```

### 5. Use expand_detail for Deep Dives
```json
{"expand_detail": true}  // Get full implementations
```

## Security Considerations

### Production Deployment

1. **Set Specific CORS Origins:**
```python
# rag_server/server.py
allow_origins=["https://your-webui-domain.com"]
```

2. **Enable API Key Authentication:**
```python
# .env
OPENAI_API_KEY=your-secret-key
```

3. **Use HTTPS:**
```bash
# Run behind nginx/caddy with SSL
```

4. **Rate Limiting:**
Consider adding rate limiting middleware for public deployments.

## Performance

### Response Times
- **Code lookup** (rag-smart with EXACT_SYMBOL): ~15-50ms
- **Documentation search** (rag-standard): ~200-500ms
- **Enhanced query** (rag-enhanced): ~500-1500ms

### Streaming
- Provides perceived performance improvement
- Chunks sent every ~50ms
- Total time same as non-streaming

## Examples

### Example 1: Code Lookup
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "rag-smart",
    "messages": [
      {"role": "user", "content": "show me AutomationCondition.eager"}
    ]
  }'
```

### Example 2: How-To Question
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "rag-enhanced",
    "messages": [
      {"role": "user", "content": "how do I create a Dagster schedule"}
    ]
  }'
```

### Example 3: With Custom Parameters
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "rag-smart",
    "messages": [
      {"role": "user", "content": "show me the Table class"}
    ],
    "repo_filter": "dagster",
    "expand_detail": true
  }'
```

## Summary

The OpenAI-compatible API makes your RAG system accessible through familiar web interfaces while maintaining all the advanced features like:

✅ Intelligent query routing
✅ Code index lookups
✅ Multi-repository support
✅ Progressive detail levels
✅ Grounded, accurate responses

Start chatting with your documentation and code through Open WebUI or LibreChat today!
