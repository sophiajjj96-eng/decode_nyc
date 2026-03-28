# Demo Flow: DecodeNYC

## Demo Overview

This demo showcases the empathetic, storytelling approach of the DecodeNYC agent, focusing on housing assistance questions. The agent translates technical algorithm specifications into human-centered narratives that help NYC residents understand how government systems make decisions about their lives.

**Key Features Demonstrated:**
- Empathetic recognition of housing crisis situations
- Structured responses with clear sections
- Explanation of fairness issues in plain language
- Actionable next steps for residents
- Visual flowcharts showing algorithm decision processes
- Generated diagrams for algorithm explanations

---

## Demo Question 1: Housing Eligibility

### Presenter Intro (5 seconds)

"Let's ask about a situation thousands of New Yorkers face every month - losing their housing and needing emergency support."

### User Question

> "I'm about to lose my apartment. I need help finding shelter. Am I eligible for housing support?"

### Agent Response

**Your Situation**

I understand you're going through a really difficult time. The stress of potentially losing your home is overwhelming, and navigating the housing system can feel impossible. Let me help you understand how the city decides who gets homelessness prevention services.

**The Algorithm: Homebase Risk Assessment**

When you apply for homelessness prevention services through Homebase (run by the Department of Homeless Services), the city uses something called the Risk Assessment Questionnaire. This is a scoring algorithm that evaluates your situation based on several factors.

## What DHS Considers

- **Prior DHS Contact** 🔴 **High Impact**
- **Length of Current Housing** 🔴 **High Impact**  
- **Income** 🟡 **Medium Impact**
- **Employment Status** ⚪ **Considered**
- **Family Size** 🟡 **Medium Impact**
- **Reason for Housing Loss** ⚪ **Considered**

## How It Works

You'll answer questions about your housing history, income, family situation, and whether you've needed DHS services before. The algorithm produces a risk score. Caseworkers then use that score to recommend whether you should receive services like rental assistance, mediation with landlords, or connections to legal aid.

_[Visual flowchart showing the decision tree appears below]_

## ⚠️ Known Fairness Issues

- **Prior DHS contact lowers your score** — the algorithm penalizes people for having needed help before. This is a documented fairness problem with the system.
- **No public documentation on exact scoring thresholds** — residents don't know what score they need to qualify
- **Limited formal appeal process** if your score is too low
- **Trained on historical DHS data from 2012** — the algorithm learned from past patterns of denial, which may perpetuate those patterns

## What You Can Do Now

✓ **Apply to Homebase anyway** — a caseworker can advocate for you even if the algorithm gives you a low score

✓ **Contact the Legal Aid Society** for eviction protection and legal representation

✓ **Call 311 for Emergency Rental Assistance** — this program does NOT use the RAQ scoring algorithm

✓ **Document your situation** — gather any eviction notices, lease documents, and proof of income before applying

---

**Follow-up questions:**

1. Is the algorithm fair to people who've needed help before?
2. Can I appeal if my score is too low?
3. What if my income situation has changed?
4. How long does the Homebase application process take?

### Expected Visuals

1. **Mermaid flowchart** (auto-displays): Shows the Homebase RAQ decision tree with branches for prior DHS contact, income level, and risk score calculation
2. **Generated diagram** (if ENABLE_IMAGE_GEN=TRUE): Gemini-generated flowchart image showing the step-by-step decision process in a visual format

### Timing Notes

- **Question delivery:** 3 seconds
- **Agent response:** 25-30 seconds (text mode) or 40-50 seconds (voice mode with audio playback)
- **Flowchart render:** 2-3 seconds
- **Total:** ~35-55 seconds depending on mode

---

## Demo Question 2: Prior DHS Contact Impact

### Presenter Intro (5 seconds)

"Now let's follow up with a critical question about fairness - one of the core issues this tool is designed to expose."

### User Question

> "What happens if I was previously in the DHS shelter system?"

### Agent Response

**The Prior Contact Penalty**

This is one of the most problematic aspects of the Homebase Risk Assessment algorithm, and I want to be direct with you about it.

**Because you've used DHS services before, the system actually lowers your score.** This is a known fairness issue — the algorithm penalizes people for having needed help in the past.

## How This Works

The algorithm treats "prior DHS contact" as a 🔴 **High Impact** factor. When the system sees that you've been in the shelter system before, it reduces your risk score. The logic is that people with prior contact are supposedly "lower risk" for homelessness.

But here's the problem: **This creates a circular trap.** The people who most needed help before are the same people who likely need help now. Yet the algorithm makes it harder for them to qualify.

## Why This Is Unfair

The Homebase algorithm was trained on historical DHS data from 2012. That means it learned from the city's past decisions about who got services and who didn't. If those past decisions had bias — and research suggests they did — the algorithm perpetuates that bias forward.

People who've been through the shelter system already know how to navigate it. They're not "low risk" — they're experienced survivors who deserve support, not penalties.

## ⚠️ Known Fairness Issues

- **Prior DHS contact lowers your score** — documented fairness problem
- **No appeals process specifically for algorithm scores** — you can't challenge the score itself
- **No transparency on weights** — DHS doesn't publish how heavily prior contact affects your final score
- **Trained on biased historical data** — the 2012 training data reflects years of unequal access to services

## What You Can Do

✓ **Apply anyway** — caseworkers have discretion to override algorithm recommendations

✓ **Explain your situation directly** — tell the caseworker why you need services now, regardless of past history

✓ **Document any changes** — new income loss, health issues, family circumstances that differ from before

✓ **Contact Legal Aid Society** — they can advocate on your behalf and know how to navigate the Homebase system

✓ **File a complaint** if denied — document the denial and ask for a supervisor review

## Your Rights

You have the right to know why you're being scored and what factors were used. You can request to see your file and ask questions about the decision process.

---

**Follow-up questions:**

1. Can I see my actual risk score?
2. What if my situation now is different from before?
3. Are there other housing programs that don't use this algorithm?
4. Who can I contact if I think the decision was wrong?

### Expected Visuals

1. **Mermaid flowchart** (auto-displays): Shows how prior DHS contact affects the scoring path
2. **Generated impact diagram** (if enabled): Visual showing how the penalty factor reduces the final score

### Timing Notes

- **Question delivery:** 2 seconds
- **Agent response:** 30-35 seconds (text mode) or 50-60 seconds (voice mode)
- **Total:** ~35-60 seconds depending on mode

---

## Demo Presentation Tips

### Opening (30 seconds)
- "Today I'm showing you DecodeNYC, a civic AI agent that helps NYC residents understand how government algorithms affect their lives."
- "Unlike typical chatbots that just answer questions, this agent acts as a translator - turning bureaucratic algorithm specifications into plain-language stories that everyday New Yorkers can understand."
- "It's built on Google's Gemini 2.5 Flash with native audio support, and it uses the NYC Algorithmic Tools Compliance Report as its data source."

### Between Questions (10 seconds)
- Point out the structured response format: situation acknowledgment → algorithm explanation → fairness issues → actionable steps
- Highlight the visual indicators (🔴🟡⚪) for impact levels
- Note the follow-up question suggestions that appear automatically

### Closing (20 seconds)
- "What makes this powerful is that it doesn't just explain what algorithms do - it explains the fairness issues, the hidden penalties, and gives people actionable next steps."
- "This is algorithmic transparency in service of residents, not bureaucracy."
- "The code is open source, and we're committed to keeping the data updated as NYC's algorithmic tools change."

---

## Technical Notes for Demo

### Backend Configuration

Ensure these settings in `backend/.env`:

```bash
GOOGLE_API_KEY=your_api_key_here
DEMO_AGENT_MODEL=gemini-2.5-flash-native-audio-preview-12-2025
ENABLE_IMAGE_GEN=TRUE  # Enable Gemini's native image generation
```

### Running the Demo

1. Start backend: `uv run --project backend uvicorn backend.main:app --reload`
2. Open browser to `http://localhost:8000/agent`
3. For voice demo: Click the voice button (speaker icon) and speak naturally
4. For text demo: Type questions in the text box

### Fallback Plan

If live demo has technical issues:
- Have screenshots ready of both question/response pairs
- Have the flowchart diagrams pre-rendered
- Can walk through the algorithm data in `backend/data/algorithms.json` directly

### Key Points to Emphasize

1. **Empathy first**: Notice how the agent acknowledges the user's stress before diving into technical details
2. **Plain language**: No jargon - "penalizes people for having needed help" instead of "negative weight for prior_dhs_contact"
3. **Fairness transparency**: Explicitly calls out known issues, doesn't hide them
4. **Actionable**: Every response ends with concrete steps the user can take
5. **Visual support**: Flowcharts help make complex decision trees understandable

---

## Expected Audience Reactions

- **Surprise** at how clearly the agent explains complex government systems
- **Recognition** of the fairness issues being real problems, not theoretical
- **Appreciation** for the actionable next steps (not just information)
- **Interest** in the structured response format and visual aids

## Questions to Anticipate

1. **"How accurate is the data?"** - Data comes directly from NYC's official Algorithmic Tools Compliance Report, updated regularly
2. **"Can it handle Spanish?"** - Yes, the agent auto-detects language and responds in Spanish or English
3. **"What about privacy?"** - The agent is designed to filter PII and not log any identifying information
4. **"Can residents actually use this?"** - Yes, it's deployed publicly and designed for accessibility
