# WebSocket API Reference

## Overview

Algorithm Explained provides a WebSocket API for bi-directional streaming with ADK (Agent Development Kit). This enables real-time text and audio communication with the civic AI agent.

## Connection

### Endpoint

```
ws://localhost:8000/ws/{user_id}/{session_id}
```

Or with HTTPS:

```
wss://yourdomain.com/ws/{user_id}/{session_id}
```

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | string | Unique identifier for the user (e.g., "user-123") |
| `session_id` | string | Unique identifier for the session (e.g., "session-abc") |

Sessions with the same `user_id` and `session_id` resume conversation history.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `proactivity` | boolean | false | Enable proactive audio (native audio models only) |
| `affective_dialog` | boolean | false | Enable affective dialog (native audio models only) |

Example with query parameters:

```
ws://localhost:8000/ws/user-123/session-abc?proactivity=true&affective_dialog=true
```

## Message Formats

### Client to Server

#### Text Message

```json
{
  "type": "text",
  "text": "What algorithmic tools does the NYPD use?"
}
```

Send as WebSocket text frame.

#### Audio Message

Send raw binary WebSocket frames containing:
- **Format**: PCM (Pulse Code Modulation)
- **Sample rate**: 16kHz
- **Bit depth**: 16-bit signed integer
- **Channels**: Mono (1 channel)
- **Encoding**: Little-endian Int16Array

Send as WebSocket binary frames (not JSON).

### Server to Client

All server messages are JSON-encoded ADK `Event` objects sent as WebSocket text frames.

#### Event Structure

```json
{
  "author": "model",
  "content": {...},
  "turnComplete": false,
  "interrupted": false,
  "inputTranscription": {...},
  "outputTranscription": {...},
  "usageMetadata": {...}
}
```

## Event Types

### Content Events

Agent's text or audio response:

```json
{
  "author": "model",
  "content": {
    "parts": [
      {
        "text": "Based on the NYC compliance data..."
      }
    ]
  },
  "partial": true
}
```

Audio content:

```json
{
  "author": "model",
  "content": {
    "parts": [
      {
        "inlineData": {
          "mimeType": "audio/pcm;rate=24000",
          "data": "base64_encoded_pcm_audio..."
        }
      }
    ]
  }
}
```

Audio format:
- **Encoding**: Base64
- **Sample rate**: 24kHz
- **Format**: PCM 16-bit signed integer
- **Decode**: base64 → Int16Array → AudioWorklet

### Input Transcription Events

Real-time transcription of user's speech:

```json
{
  "inputTranscription": {
    "text": "What tools does the",
    "finished": false
  }
}
```

Final transcription:

```json
{
  "inputTranscription": {
    "text": "What tools does the NYPD use?",
    "finished": true
  }
}
```

### Output Transcription Events

Real-time transcription of agent's speech:

```json
{
  "outputTranscription": {
    "text": "Based on the NYC compliance",
    "finished": false
  }
}
```

### Turn Complete Events

Signals end of agent's response:

```json
{
  "turnComplete": true
}
```

Reset UI state when received.

### Interrupted Events

User interrupted agent's response:

```json
{
  "interrupted": true
}
```

Stop audio playback and clear partial responses.

### Usage Metadata Events

Token usage information:

```json
{
  "usageMetadata": {
    "promptTokenCount": 150,
    "candidatesTokenCount": 80,
    "totalTokenCount": 230
  }
}
```

## Connection Lifecycle

### 1. Connect

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/user-123/session-abc');
```

### 2. Handle Connection

```javascript
ws.onopen = () => {
  console.log('Connected to ADK agent');
};
```

### 3. Send Messages

```javascript
// Text message
ws.send(JSON.stringify({
  type: "text",
  text: "What tools does NYC use?"
}));

// Audio message (binary)
ws.send(pcmAudioBuffer);
```

### 4. Receive Events

```javascript
ws.onmessage = (event) => {
  const adkEvent = JSON.parse(event.data);
  
  if (adkEvent.content) {
    // Handle content
  }
  if (adkEvent.inputTranscription) {
    // Handle transcription
  }
  if (adkEvent.turnComplete) {
    // Reset UI state
  }
};
```

### 5. Handle Disconnection

```javascript
ws.onclose = () => {
  console.log('Disconnected, reconnecting...');
  setTimeout(reconnect, 5000);
};
```

## Example: Text-Only Client

```javascript
const userId = 'demo-user';
const sessionId = `session-${Date.now()}`;
const ws = new WebSocket(`ws://localhost:8000/ws/${userId}/${sessionId}`);

ws.onopen = () => {
  // Send text message
  ws.send(JSON.stringify({
    type: "text",
    text: "What algorithmic tools does the NYPD use?"
  }));
};

ws.onmessage = (event) => {
  const adkEvent = JSON.parse(event.data);
  
  // Display text response
  if (adkEvent.content?.parts) {
    for (const part of adkEvent.content.parts) {
      if (part.text) {
        console.log('Agent:', part.text);
      }
    }
  }
  
  // Turn complete
  if (adkEvent.turnComplete) {
    console.log('Response complete');
  }
};
```

## Example: Voice Client

```javascript
// Setup audio recorder (16kHz PCM)
const audioContext = new AudioContext({ sampleRate: 16000 });
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
const source = audioContext.createMediaStreamSource(stream);

// Connect to audio worklet
await audioContext.audioWorklet.addModule('pcm-recorder-processor.js');
const recorderNode = new AudioWorkletNode(audioContext, 'pcm-recorder-processor');
source.connect(recorderNode);

// Send audio to server
recorderNode.port.onmessage = (event) => {
  const float32Audio = event.data;
  const pcmData = convertFloat32ToPCM(float32Audio);
  ws.send(pcmData); // Binary frame
};

// Receive audio from server
ws.onmessage = (event) => {
  const adkEvent = JSON.parse(event.data);
  
  if (adkEvent.content?.parts) {
    for (const part of adkEvent.content.parts) {
      if (part.inlineData?.mimeType.startsWith('audio/pcm')) {
        const audioData = base64ToInt16Array(part.inlineData.data);
        playAudio(audioData); // Send to audio worklet
      }
    }
  }
};
```

## Error Handling

### Connection Errors

```javascript
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
  // Implement retry logic
};
```

### Timeout Handling

```javascript
// Implement ping/pong or activity timeout
let activityTimeout;

function resetTimeout() {
  clearTimeout(activityTimeout);
  activityTimeout = setTimeout(() => {
    console.log('No activity, reconnecting...');
    ws.close();
  }, 60000); // 60 seconds
}

ws.onmessage = (event) => {
  resetTimeout();
  // Handle event...
};
```

## Rate Limits

### Current Implementation

No enforced rate limits. Production considerations:
- Implement per-user rate limiting
- Throttle dataset API calls
- Cache common queries

### NYC Open Data Limits

- Socrata platform has rate limits
- Typically 1000 requests/hour for unauthenticated
- 10,000 requests/hour with app token

## Authentication

### Current State

No authentication required. Anyone can connect.

### Future Considerations

For production deployment:
- Add JWT authentication
- Validate user_id ownership
- Implement session tokens
- Rate limiting per authenticated user

## Response Modalities

### Native Audio Models

Models with "native-audio" in name:
- Response modality: AUDIO
- Includes automatic transcription
- Streams 24kHz PCM audio

### Half-Cascade Models

Other Gemini models:
- Response modality: TEXT
- No audio output
- Faster for text-only use

Detection is automatic based on model name in `backend/.env`.

## Integration Examples

### Python Client

```python
import asyncio
import websockets
import json

async def chat():
    uri = "ws://localhost:8000/ws/user-123/session-abc"
    
    async with websockets.connect(uri) as ws:
        # Send message
        await ws.send(json.dumps({
            "type": "text",
            "text": "What tools does the NYPD use?"
        }))
        
        # Receive response
        async for message in ws:
            event = json.loads(message)
            
            if event.get('content'):
                for part in event['content']['parts']:
                    if 'text' in part:
                        print(part['text'], end='', flush=True)
            
            if event.get('turnComplete'):
                break

asyncio.run(chat())
```

### Node.js Client

```javascript
const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8000/ws/user-123/session-abc');

ws.on('open', () => {
  ws.send(JSON.stringify({
    type: 'text',
    text: 'What tools does the NYPD use?'
  }));
});

ws.on('message', (data) => {
  const event = JSON.parse(data);
  
  if (event.content?.parts) {
    event.content.parts.forEach(part => {
      if (part.text) process.stdout.write(part.text);
    });
  }
  
  if (event.turnComplete) {
    console.log('\nResponse complete');
    ws.close();
  }
});
```

## Health Check

### HTTP Endpoint

```
GET http://localhost:8000/health
```

Response:
```json
{
  "ok": true
}
```

Use for:
- Load balancer health checks
- Monitoring systems
- Uptime verification

## Resources

- [ADK Events Documentation](https://google.github.io/adk-docs/)
- [WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
