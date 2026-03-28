# Quick Start

Get DecodeNYC running in 60 seconds.

## Install and Run

```bash
cd algorithm-explained
uv sync
cp backend/env.example backend/.env
# Edit backend/.env and add your GOOGLE_API_KEY
export SSL_CERT_FILE=$(uv run --project backend python -m certifi)
uv run --project backend uvicorn backend.main:app --reload
```

Open `http://localhost:8000`

## Get API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Create API key
3. Add to `backend/.env`: `GOOGLE_API_KEY=your_key_here`

## Text Mode

1. Type your question in the input field
2. Press Enter or click Send
3. Read the agent's response

**Example questions:**
- "What algorithmic tools does the NYPD use?"
- "Does NYC use facial recognition?"
- "What algorithms does NYC Housing use?"
- "How do police algorithms work?"

The agent queries NYC's official Algorithmic Tools Compliance Report and provides factual answers with agency citations.

## Voice Mode

1. Click "Voice" toggle in header
2. Click "Start Discussion"
3. Grant microphone permissions
4. Speak naturally

**Tips:**
- Speak clearly at normal pace
- Wait for agent to finish before responding
- Minimize background noise
- Use complete sentences

**Requirements:**
- Chrome, Edge, or Safari (Firefox has limitations)
- HTTPS or localhost
- Working microphone and speakers

Click "Tap to stop" to end the session.

## Browser Support

**Fully supported:**
- Chrome 90+
- Edge 90+
- Safari 14+

**Limited:**
- Firefox 88+ (Web Audio limitations)

**Not supported:**
- Internet Explorer
- Chrome iOS (WebRTC limitations)

## Troubleshooting

**Voice mode not working?**
- Check microphone permissions in browser
- Verify HTTPS or localhost
- Try Chrome or Edge

**No response?**
- Check WebSocket connection status in UI
- Refresh page to reconnect
- Check backend terminal for errors
- Verify API key is valid

**Slow responses?**
- Dataset fetches 200 rows per query
- Text mode is faster than voice mode
- Specific questions are faster

**Audio not playing?**
- Check tab isn't muted
- Verify speakers are connected
- Check system volume

## Next Steps

- [REFERENCE.md](REFERENCE.md) - Technical architecture and API
- [DEVELOPMENT.md](DEVELOPMENT.md) - Contributing and development
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deploy to Cloud Run
