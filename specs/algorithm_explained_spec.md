# Algorithm, Explained — Technical Spec
**GDG NYC Build With AI Hackathon · Creative Storyteller Track**

> "Most NYC residents are affected by government algorithms they've never heard of. We make them visible."

---

## 1. What We're Building

A voice-first multimodal AI agent. The user speaks their situation — the agent responds with **narration (voice) + explanation (text) + visual (generated image) simultaneously** in one interleaved output stream.

**Core demo flow:**
1. User speaks: *"I'm about to lose my apartment. Am I eligible for housing support?"*
2. Gemini detects context → maps to Homebase RAQ algorithm
3. Single API call returns: narration script + flowchart image + info cards, all streaming together
4. User asks follow-up: *"What if I was in the shelter system before?"*
5. Agent responds in real-time, personalizing to their situation

---

## 2. The 4 Algorithms We Cover

Pre-process these into JSON before hackathon day. Do NOT try to parse PDFs live.

```json
[
  {
    "id": "homebase_raq",
    "name": "Homebase Risk Assessment Questionnaire",
    "agency": "Department of Homeless Services",
    "trigger_keywords": ["shelter", "homeless", "eviction", "housing", "apartment", "lose my home"],
    "plain_summary": "Scores households on 20+ factors to decide who gets homelessness prevention services.",
    "how_it_works": "Applicants answer questions about housing history, income, family size, and prior DHS contact. The algorithm produces a risk score. Staff use that score to decide eligibility.",
    "inputs": ["prior DHS contact", "length of current housing", "income", "employment status", "family size", "reason for housing loss"],
    "key_weights": {"prior_dhs_contact": "high", "housing_length": "high", "income": "medium", "family_size": "medium"},
    "outputs": "Risk score → recommendation for or against services",
    "date_first_used": "2012-06",
    "fairness_concerns": [
      "Prior DHS contact lowers your score — penalizes people for having needed help before",
      "No public documentation on exact scoring thresholds",
      "Limited formal appeal process if score is too low",
      "Trained on historical DHS data from 2012 — embeds past patterns of denial"
    ],
    "what_you_can_do": [
      "Apply to Homebase anyway — a caseworker can advocate even with a low score",
      "Contact Legal Aid Society for eviction protection",
      "Call 311 for Emergency Rental Assistance (does not use RAQ score)"
    ]
  },
  {
    "id": "myschools",
    "name": "MySchools — Gale-Shapley Matching Algorithm",
    "agency": "NYC Public Schools",
    "trigger_keywords": ["school", "school assignment", "my kid", "high school", "application", "waitlist"],
    "plain_summary": "Matches students to schools based on ranked preferences, seat availability, and student profiles.",
    "how_it_works": "Uses the Gale-Shapley deferred acceptance algorithm. Students rank schools; schools rank students. The algorithm finds a stable match. In 2024, a 'Probability of Acceptance' feature was added.",
    "inputs": ["home address", "poverty status", "student biographical info", "school rankings submitted by student", "seat availability"],
    "outputs": "School match for each student; probability of acceptance score (2024+)",
    "date_first_used": "2018-08",
    "fairness_concerns": [
      "Home address is an input — students in lower-income neighborhoods may have fewer competitive options nearby",
      "Probability of Acceptance score may discourage students from applying to certain schools",
      "Algorithm logic is not fully public"
    ],
    "what_you_can_do": [
      "Appeal through the NYC DOE appeals process within the deadline",
      "Apply to specialized high schools separately (different process)",
      "Contact your school district office for waitlist status"
    ]
  },
  {
    "id": "acs_repeat_maltreatment",
    "name": "ACS Repeat Maltreatment Predictive Model",
    "agency": "Administration for Children's Services",
    "trigger_keywords": ["ACS", "child services", "flagged", "investigation", "family services", "child welfare"],
    "plain_summary": "Predicts likelihood of future child maltreatment to prioritize ACS caseworker attention.",
    "how_it_works": "Trained on historical ACS administrative data. Takes prior investigation history and family data as inputs. Outputs a ranked list of open cases for caseworker review.",
    "inputs": ["prior investigation history", "administrative data about prior family involvement"],
    "outputs": "Rank-ordered list of open investigation cases by predicted risk",
    "date_first_used": "2017-07",
    "identifying_info": true,
    "fairness_concerns": [
      "Prior ACS contact increases your risk score — same circular trap as Homebase",
      "Trained on historical data that may embed racial and socioeconomic bias",
      "Families may not know they are being scored",
      "High-stakes decisions (family separation) influenced by a model"
    ],
    "what_you_can_do": [
      "You have the right to know why ACS is investigating",
      "You can request a fair hearing",
      "Contact a family defense attorney — Legal Aid Society has a family defense practice"
    ]
  },
  {
    "id": "shotspotter",
    "name": "ShotSpotter",
    "agency": "New York Police Department",
    "trigger_keywords": ["police", "cops", "neighborhood", "gunshot", "shotspotter", "surveillance", "patrol"],
    "plain_summary": "Acoustic gunshot detection system that triggers police dispatch based on audio signals.",
    "how_it_works": "Microphones placed throughout neighborhoods analyze audio signals for potential gunshots. Algorithm determines location and triggers police dispatch. Training data is proprietary to vendor.",
    "inputs": ["audio signals from neighborhood microphones"],
    "outputs": "Location of detected sound + police dispatch recommendation",
    "date_first_used": "2015-03",
    "vendor": "ShotSpotter (now SoundThinking)",
    "vendor_desc": "Training data is proprietary to the vendor — neither residents nor city officials can audit it",
    "fairness_concerns": [
      "Sensor placement concentrated in specific neighborhoods — not evenly distributed citywide",
      "Algorithm is a black box — vendor training data not disclosed",
      "Known false positive rate: sounds that are not gunshots trigger police response",
      "Disproportionate deployment in communities of color"
    ],
    "what_you_can_do": [
      "File a complaint with the CCRB (Civilian Complaint Review Board) for wrongful police contact",
      "Contact the Legal Aid Society if you were stopped or harassed",
      "Attend Community Board meetings — sensor placement decisions go through community input"
    ]
  }
]
```

---

## 3. Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Voice input | Gemini Live API (`gemini-2.0-flash-live`) | Real-time, barge-in supported |
| Interleaved output | `gemini-2.5-flash-preview-05-20` | `responseModalities: ["TEXT", "IMAGE"]` |
| TTS narration | Gemini Live API audio output | Same session as voice input |
| NYC geo data | NYC Open Data NTA boundaries | GeoJSON for neighborhood map |
| Backend | Google Cloud Run + Google ADK | Agent orchestration |
| Frontend | React | Streaming UI |

---

## 4. API Call Structure

### 4a. Voice Input (Live API)
```javascript
const session = await client.live.connect({
  model: 'gemini-2.0-flash-live',
  config: {
    responseModalities: ['AUDIO', 'TEXT'],
    speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Charon' } } }
  }
});

// Send audio stream from mic
session.sendRealtimeInput({ audio: { data: audioChunk, mimeType: 'audio/pcm' } });

// Receive transcription
session.on('message', (msg) => {
  if (msg.serverContent?.inputTranscription) {
    const userText = msg.serverContent.inputTranscription.text;
    triggerAlgorithmDetection(userText);
  }
});
```

### 4b. Algorithm Detection
```javascript
function detectAlgorithm(userText) {
  const lower = userText.toLowerCase();
  for (const algo of ALGORITHMS) {
    if (algo.trigger_keywords.some(k => lower.includes(k))) {
      return algo;
    }
  }
  return null; // fallback: ask Gemini to classify
}
```

### 4c. Interleaved Output — THE CORE CALL
This is the mandatory tech. One call, text + image simultaneously.

```javascript
async function generateInterleavedOutput(algo, userSituation) {
  const response = await fetch('https://api.anthropic.com/v1/messages', {
  // NOTE: use Google AI SDK in actual implementation, not Anthropic
  // Shown here for structure illustration
  });

  // ACTUAL Google AI SDK call:
  const result = await googleAI.models.generateContent({
    model: 'gemini-2.5-flash-preview-05-20',
    contents: [{
      role: 'user',
      parts: [{
        text: `
You are a civic transparency assistant explaining NYC government algorithms.

User situation: "${userSituation}"
Algorithm: ${JSON.stringify(algo)}

Generate an interleaved response with:
1. A narration script (conversational, 3-4 paragraphs, tone: clear + empathetic, NOT bureaucratic)
2. An image prompt for a simple flowchart showing how this algorithm makes decisions

Format your response as:
[NARRATION]
...your narration text...
[/NARRATION]
[IMAGE_PROMPT]
...your image generation prompt...
[/IMAGE_PROMPT]
        `
      }]
    }],
    generationConfig: {
      responseModalities: ['TEXT', 'IMAGE']  // KEY: interleaved output
    }
  });

  // Parse interleaved content blocks
  const textBlocks = result.candidates[0].content.parts
    .filter(p => p.text)
    .map(p => p.text);

  const imageBlocks = result.candidates[0].content.parts
    .filter(p => p.inlineData)
    .map(p => p.inlineData); // base64 image data

  return { textBlocks, imageBlocks };
}
```

### 4d. Streaming to Frontend
```javascript
// Stream narration text + trigger TTS simultaneously
async function streamResponse(textBlocks, imageBlocks) {
  for (const block of textBlocks) {
    // 1. Stream text to UI word by word
    streamToUI(block);
    // 2. Send to TTS (Gemini Live audio out)
    await ttsSession.send(block);
  }
  // 3. Display generated image(s) inline
  for (const img of imageBlocks) {
    displayImageInUI(`data:image/png;base64,${img.data}`);
  }
}
```

---

## 5. Frontend Component Structure

```
App
├── VoiceButton          ← mic on/off, animated when listening
├── TranscriptBubble     ← user's words appear as they speak
├── ResponseStream       ← main output area
│   ├── NarrationText    ← streams in word by word
│   ├── AlgoFlowChart    ← generated image (fades in)
│   ├── FactCards        ← "what it looks at" + "fairness concerns"
│   └── ActionSteps      ← "what you can do"
└── FollowUpChips        ← suggested next questions
```

### Key UI rules
- Narration text and image appear **at the same time** — not sequentially
- FactCards fade in with ~200ms stagger after narration starts
- Follow-up chips always visible at bottom
- No loading spinner — start streaming immediately, content builds progressively

---

## 6. Pre-processed Data (Do This Before Hackathon Day)

**Don't parse PDFs live. Pre-bake everything.**

```
/data
  algorithms.json       ← the 4 algorithm objects above
  nta_boundaries.geojson ← NYC neighborhood boundaries (from NYC Open Data)
  flowchart_templates/
    homebase_raq.png    ← pre-generate or template-render
    myschools.png
    acs_model.png
    shotspotter.png
```

For flowchart images: either pre-generate with Imagen before the hackathon, or use a simple canvas-rendered template at runtime. Do NOT try to generate complex diagrams live — too slow for demo.

---

## 7. Day-by-Day Plan

### Day 1 — Core pipeline only
- [ ] Live API voice input → transcript
- [ ] Keyword → algorithm detection
- [ ] Single interleaved API call → text + image output
- [ ] Basic streaming UI (text streams in, image appears)
- [ ] TTS narration plays while text streams

**Definition of done for Day 1:** User speaks → agent responds with voice + text + one image. That's a demo.

### Day 2 — Polish + NYC map
- [ ] Follow-up question handling (conversation history)
- [ ] FactCards + ActionSteps UI components
- [ ] Follow-up chips
- [ ] NYC NTA map: show which neighborhoods are most affected by each algorithm (seeded data ok)
- [ ] Demo rehearsal × 3
- [ ] Pitch deck: architecture diagram + working demo screenshot

---

## 8. Demo Script (5 min)

**0:00–0:30 — Hook**
> "Most New Yorkers are affected by government algorithms every day. School placement. Housing eligibility. Police dispatch. They've never seen them. We built the tool that shows them."

**0:30–3:00 — Live demo**
- Ask a judge: "Can you describe a situation where you've interacted with a city service?"
- Type or speak it into the app
- Show the interleaved output streaming
- Ask a follow-up out loud — agent responds in real time

**3:00–4:00 — Tech**
> "One Gemini API call. `responseModalities: ['TEXT', 'IMAGE']`. Narration, visual, and audio — simultaneously. No stitching, no pipeline."

**4:00–5:00 — Vision**
> "NYC has over 100 algorithmic tools. We cover 4 today. The architecture scales to all of them. Every resident deserves to understand the systems making decisions about their life."

---

## 9. Judging Criteria Checklist

| Criterion | How we hit it |
|---|---|
| Beyond the text box | Voice in, voice + image out. No typing. |
| Live + context-aware | Live API, barge-in, follow-up memory |
| Interleaved output | `responseModalities: ["TEXT", "IMAGE"]` — mandatory tech ✓ |
| Google Cloud native | Cloud Run + ADK + Gemini APIs |
| Civic impact | Government transparency, housing/policing/education equity |
| Surfaces inequities | Explicit fairness concerns per algorithm |
| Demo clarity | Story-driven, real working software, architecture diagram |

---

## 10. Repo Structure Suggestion

```
algorithm-explained/
├── backend/
│   ├── main.py               ← Cloud Run entry point
│   ├── agent.py              ← ADK agent definition
│   ├── algorithm_mapper.py   ← keyword → algorithm detection
│   └── data/
│       └── algorithms.json   ← pre-processed algorithm data
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── VoiceButton.jsx
│   │   │   ├── ResponseStream.jsx
│   │   │   ├── FactCards.jsx
│   │   │   └── NycMap.jsx
│   │   └── hooks/
│   │       ├── useLiveApi.js   ← Gemini Live API connection
│   │       └── useStream.js    ← streaming text handler
│   └── public/
│       └── flowcharts/         ← pre-generated images
└── README.md
```

---

*Good luck. Ship the pipeline first. Polish second.*
