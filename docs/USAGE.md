# Usage Guide

## Text Mode

### Starting a Conversation

1. Open `http://localhost:8000`
2. Type your question in the text input field
3. Press Enter or click Send
4. Read the agent's response

### Example Questions

**About algorithmic tools:**
- "What algorithmic tools does the NYPD use?"
- "Does NYC use facial recognition?"
- "Tell me about predictive policing"

**About specific agencies:**
- "What algorithms does NYC Housing use?"
- "How does the Department of Education use AI?"
- "What automated systems does HRA have?"

**About impact:**
- "How do housing algorithms work?"
- "Can algorithms affect my benefits?"
- "What rights do I have regarding algorithms?"

### Response Format

The agent provides:
- Direct answers based on NYC compliance data
- Specific agency and tool names
- Purpose and description of each tool
- Plain language explanations

Example response:
```
Based on the NYC Algorithmic Tools Compliance Report, the NYPD uses:

1. Domain Awareness System (DAS)
   Purpose: Real-time crime analysis and resource deployment
   
2. Facial Recognition System
   Purpose: Identify suspects from video footage

3. ShotSpotter
   Purpose: Detect and locate gunshot sounds
```

## Voice Mode

### Starting Voice Interaction

1. Click the **"Voice"** toggle in the header
2. Click **"Start Discussion"**
3. Grant microphone permissions when prompted
4. Start speaking naturally

### During Voice Conversation

**Visual feedback:**
- "Listening..." status when recording
- Real-time transcription of your words
- "Agent speaking..." when responding
- Waveform animation

**Audio feedback:**
- Agent responds with natural speech
- Transcription displays simultaneously
- Clear, conversational tone

### Ending Voice Session

Click **"Tap to stop"** to end the session. The agent finishes current response before stopping.

### Voice Best Practices

**For clear recognition:**
- Speak at normal pace
- Use complete sentences
- Minimize background noise
- Wait for agent to finish before speaking

**For better answers:**
- Be specific: "NYPD facial recognition" vs. "police AI"
- Ask one thing at a time
- Follow up naturally: "Tell me more about that"

### Voice Mode Requirements

- HTTPS or localhost
- Modern browser (Chrome, Edge, Safari)
- Working microphone
- Stable internet connection

## Switching Modes

Click the mode toggle buttons in the header anytime to switch between Text and Voice modes. Your conversation history is preserved.

## Conversation Features

### Context Maintenance

The agent remembers your conversation:

```
You: "What tools does the NYPD use?"
Agent: [Lists NYPD tools]

You: "How accurate is the facial recognition system?"
Agent: [Refers back to NYPD facial recognition from previous turn]
```

### Multi-Turn Clarification

```
You: "Tell me about housing algorithms"
Agent: "NYC Housing uses several tools. Which one interests you?"
You: "The rental assistance one"
Agent: [Provides specific details]
```

### Dataset-Grounded Responses

All answers cite official NYC compliance data:
- Agency names
- Tool names and purposes
- Compliance report fields
- No speculation or invented information

## Understanding Responses

### When the Agent Can Help

The agent excels at:
- Explaining what algorithmic tools NYC agencies use
- Describing tool purposes and functions
- Identifying which agencies use which tools
- Providing official compliance information

### When the Agent Can't Help

The agent will tell you when:
- Dataset doesn't contain relevant information
- Question is outside dataset scope
- More context needed

Example: "The dataset doesn't include information about Fire Department algorithms. Try asking about NYPD, Housing, Education, or Social Services."

## Tips for Better Results

### Be Specific

**Better:**
- "What facial recognition tools does the NYPD use?"
- "How does NYC Housing Authority use algorithms for tenant screening?"

**Less effective:**
- "Does NYC use AI?"
- "Tell me about algorithms"

### Use Agency Names

**Effective agencies in dataset:**
- NYPD (New York City Police Department)
- NYC Housing (Housing Preservation and Development)
- DOE (Department of Education)
- HRA (Human Resources Administration)
- ACS (Administration for Children's Services)

### Ask Follow-Up Questions

Build on previous responses:
```
1. "What tools does the NYPD use?"
2. "How does the ShotSpotter system work?"
3. "What data does it collect?"
```

## UI Indicators

### Status Messages

- **ready**: Idle, waiting for input
- **thinking...**: Processing your question
- **listening...**: Recording your voice
- **agent speaking...**: Playing audio response
- **connected**: WebSocket connected
- **reconnecting...**: Connection lost, retrying
- **error**: Something went wrong

### Message States

- **Solid bubbles**: Complete messages
- **Streaming bubbles**: Partial responses (slightly transparent)
- **Typing indicator**: Three animated dots

## Accessibility

### Keyboard Navigation

- Tab through interactive elements
- Enter to send messages
- Escape to close modals (future)

### Screen Reader Support

Currently limited - text mode recommended for screen reader users. Voice mode transcriptions are visible text.

## Performance Tips

### For Fast Responses

- Text mode is faster than voice mode
- Specific questions retrieve fewer rows
- Shorter questions process quicker

### For Voice Quality

- Use wired headphones to reduce echo
- Minimize background noise
- Stable internet for smooth streaming

## Session Management

### Session IDs

Sessions are identified by random IDs:
- Generated on page load
- Preserved during reconnections
- Reset on page refresh

### Session Data

What's preserved:
- Conversation history
- Dataset query cache (in memory)
- Agent state

What's reset:
- On server restart
- On page refresh
- After 24 hours (future)

## Advanced Usage

### Custom Session IDs

Currently not exposed in UI. Future: URL parameters for persistent sessions.

### Export Conversations

Currently not supported. Future: Download transcript button.

### Multiple Tabs

Each browser tab creates independent session. Conversations don't sync across tabs.

## Troubleshooting

### Agent Doesn't Respond

1. Check WebSocket status indicator
2. Refresh page to reconnect
3. Check backend logs for errors
4. Verify API key is valid

### Transcription Missing

1. Verify native audio model in use
2. Check audio input is working
3. Review browser console for errors

### Audio Not Playing

1. Check browser audio permissions
2. Unmute tab
3. Verify speakers/headphones connected
4. Check system volume

### Poor Response Quality

1. Be more specific in questions
2. Use agency names when known
3. Ask one thing at a time
4. Dataset may not contain information - agent will say so

## Next Steps

- [API Reference](API.md) - Integrate programmatically
- [Dataset Documentation](DATASET.md) - Understand data retrieval
- [Architecture](ARCHITECTURE.md) - Technical details
