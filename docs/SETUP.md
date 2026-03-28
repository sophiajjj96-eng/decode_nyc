# Usage Guide

## Getting Started

After installing and configuring the application (see [Setup Guide](SETUP.md)), open `http://localhost:8000` in your browser.

You'll see the "Audit the Algorithm" interface with two modes: **Text** and **Voice**.

## Text Mode

### Basic Usage

1. **Type your question** in the text input field
2. **Press Enter** or click the Send button
3. **Read the answer** in the chat area

The agent queries the official NYC Algorithmic Tools Compliance Report and provides factual answers with agency citations.

### Example Questions

**General queries:**
- "What algorithmic tools does NYC use?"
- "How do government algorithms affect me?"
- "What is the Algorithmic Tools Compliance Report?"

**Agency-specific:**
- "Does the NYPD use AI?"
- "What algorithmic tools does NYC Housing use?"
- "How does the Department of Education use algorithms?"

**Tool-specific:**
- "Does NYC use facial recognition?"
- "Tell me about predictive policing in NYC"
- "What automated systems does HRA use?"

**Impact-focused:**
- "How might housing algorithms affect my application?"
- "Can police algorithms predict crime?"
- "Are algorithms used for school admissions?"

### Response Quality

Responses are based on:
- Official NYC Open Data from Algorithmic Tools Compliance Report
- Up to 8 most relevant dataset entries
- Keyword-based retrieval with domain-specific ranking

The agent will:
- Cite specific agencies and tools
- Explain technical concepts in plain language
- Admit when data is insufficient
- Provide context about algorithmic impact

## Voice Mode

### Starting a Conversation

1. **Click the "Voice" toggle** in the header
2. **Click "Start Discussion"** button
3. **Grant microphone permissions** when prompted
4. **Speak naturally** - the agent listens continuously

### During Conversation

**You'll see:**
- Real-time transcription of your words as you speak
- Visual feedback (listening/speaking states)
- Agent's spoken response with transcription
- Waveform animation when active

**The agent:**
- Transcribes your speech in real-time
- Queries the NYC dataset when needed
- Responds with natural audio
- Maintains conversation context

### Stopping the Session

Click **"Tap to stop"** to end the voice session. You can restart anytime by clicking "Start Discussion" again.

### Voice Mode Requirements

**Browser:**
- Chrome (recommended)
- Edge
- Safari
- Firefox (limited support)

**Connection:**
- HTTPS or localhost required for microphone access
- Stable internet connection for streaming

**Hardware:**
- Working microphone
- Speakers or headphones

### Tips for Better Voice Recognition

- **Speak clearly** at normal pace
- **Minimize background noise**
- **Wait for response** before asking follow-up
- **Use full sentences** rather than fragments
- **Avoid interrupting** during agent responses

## Understanding Responses

### Dataset Citations

Responses reference specific NYC agencies and tools:

```
"Based on the NYC compliance data, the NYPD uses several algorithmic tools including:

1. Facial Recognition System
   Agency: New York City Police Department
   Purpose: Identify suspects from video footage
   
2. ShotSpotter
   Agency: NYPD
   Purpose: Detect and locate gunshot sounds"
```

### Data Limitations

The agent will tell you when:
- Dataset doesn't contain relevant information
- Question is outside scope of available data
- More specific question needed

Example: "The dataset doesn't contain information about algorithms used by the Fire Department. Try asking about NYPD, Housing, Education, or Human Resources."

### Conversation Context

The agent maintains context across multiple turns:

```
You: "What tools does the NYPD use?"
Agent: "The NYPD uses facial recognition, ShotSpotter..."

You: "How accurate are they?"
Agent: "Based on the compliance data for the NYPD tools..."
```

Sessions are preserved across reconnections with the same session ID.

## UI Elements

### Header

- **Title**: "Audit the Algorithm"
- **Status**: Shows connection state (ready, listening, thinking, error)
- **Mode Toggle**: Switch between Text and Voice modes

### Chat Area

- **User messages**: Dark bubbles on the right
- **Agent messages**: White bubbles on the left
- **Streaming indicator**: Partial responses show with visual feedback
- **Auto-scroll**: Automatically scrolls to latest message

### Footer

**Text Mode:**
- Text input area with auto-expanding textarea
- Send button

**Voice Mode:**
- Microphone button with state indicators
- Waveform visualization when active
- Status labels (Start Discussion, Tap to stop, Tap to interrupt)

## Keyboard Shortcuts

**Text Mode:**
- `Enter`: Send message
- `Shift + Enter`: Add newline in textarea

**Voice Mode:**
- `Space`: Toggle microphone (when in voice mode)

## Browser Compatibility

### Fully Supported

- Chrome 90+ (recommended)
- Edge 90+
- Safari 14+

### Limited Support

- Firefox 88+ (Web Audio API limitations)
- Opera 76+

### Not Supported

- Internet Explorer
- Chrome iOS (WebRTC limitations)

## Performance Expectations

### Text Mode

- **Response time**: 1-3 seconds for typical queries
- **Dataset query**: ~500ms to fetch and filter 200 rows
- **Streaming**: Incremental text updates as agent generates

### Voice Mode

- **End-to-end latency**: 500-1500ms
- **Transcription**: Real-time with 200-500ms delay
- **Audio streaming**: Chunked playback with minimal buffering

## Privacy and Data

### What's Sent to Google

- Your text or voice input
- NYC dataset context (public data)
- Session metadata (user_id, session_id)

### What's Stored

- Session history in memory (cleared on restart)
- No persistent storage of conversations
- No user authentication or tracking

### NYC Open Data

All dataset queries use public NYC Open Data API:
- No authentication required
- Subject to Socrata platform rate limits
- Data is publicly accessible compliance reports

## Advanced Features

### Session Management

Sessions are identified by `user_id` and `session_id`:
- Same IDs = resume conversation
- Different IDs = new conversation
- Sessions stored in memory (lost on restart)

### Proactivity (Native Audio Models Only)

Enable in voice mode for:
- Agent proactively responds without explicit prompts
- Natural interjections
- Clarifying questions

Currently not exposed in UI - future enhancement.

### Affective Dialog (Native Audio Models Only)

Enable for:
- Emotional cue detection
- Adaptive tone and response style
- More empathetic responses

Currently not exposed in UI - future enhancement.

## Getting Help

### Check Backend Logs

Backend terminal shows detailed logs:
- WebSocket connections
- ADK event stream
- Dataset queries
- Error messages

### Browser Console

Press F12 to open DevTools and check:
- WebSocket messages
- Audio worklet status
- JavaScript errors

### Common Questions

**Q: Why is voice mode not working?**
A: Check HTTPS/localhost requirement, microphone permissions, and browser compatibility.

**Q: Why are responses slow?**
A: Dataset fetches 200 rows per query. Consider caching for production.

**Q: Can I use a different dataset?**
A: Yes, modify `DATASET_URL` in `.env` and update retrieval logic in `backend/civic_agent/agent.py`.

**Q: How do I add more tools?**
A: Add tool functions in `backend/civic_agent/agent.py` and include in agent's `tools` list. See [Development Guide](DEVELOPMENT.md).

## Next Steps

- [Usage Guide](USAGE.md) - Learn interaction patterns
- [API Reference](API.md) - Build custom clients
- [Development Guide](DEVELOPMENT.md) - Contribute features
