# Privacy-Safe Architecture

## Overview

DecodeNYC uses a privacy-first architecture designed to detect algorithmic bias patterns without compromising user privacy.

## Privacy Controls

### 1. No User Tracking

**What we DO NOT collect**:
- User IDs or account identifiers
- Session IDs linked to individuals
- IP addresses
- Device fingerprints
- Geolocation data
- Timestamps linked to user sessions

**Storage**: All conversation state is in-memory only and expires when the browser session ends.

### 2. Anonymous Question Logging

**What we collect**:
- Question text only
- Timestamp (not linked to users)
- Algorithm context (which algorithm the question relates to)

**Purpose**: Detect bias patterns by analyzing which questions indicate confusion or skepticism across all users.

**Example log entry**:
```json
{
  "question": "Why is my score lower at my income level?",
  "algorithm": "Housing and homelessness",
  "timestamp": "2026-03-28T10:30:00Z"
}
```

### 3. PII Filtering in Responses

**System Prompt Directive**: The AI agent is explicitly instructed to filter and anonymize Personally Identifiable Information (PII) in all responses.

**How it works**:
- Agent identifies PII in user input (names, addresses, case numbers, SSNs)
- Responses use generic references instead of specific identifiers
- Example: "your neighborhood" instead of "123 Main Street, Bronx"

**Limitations**: Gemini's PII filtering is best-effort and not 100% guaranteed. Users should avoid sharing sensitive personal information.

### 4. Data Retention

- **Conversation history**: In-memory only, cleared on disconnect
- **Question logs**: Stored indefinitely for bias research
- **No user profiles**: System does not build or maintain user profiles

## Technical Accuracy of "Privacy-Safe" Claim

**Yes, this is defensible** based on:
1. No persistent user identification or tracking
2. Anonymous question logging (content only, no metadata)
3. In-memory session storage
4. AI-level PII filtering instructions
5. No third-party analytics or tracking scripts

**Recommended disclaimer for presentation**:
> "Questions are logged anonymously to identify algorithmic bias patterns and improve civic transparency. No personal information is stored or tracked."

## Comparison to Industry Standards

| Practice | DecodeNYC | Typical Chatbot |
|----------|-----------|-----------------|
| User accounts | No | Yes |
| Session tracking | In-memory only | Persistent database |
| Question logging | Anonymous | Linked to user ID |
| IP address storage | No | Yes (for analytics) |
| Analytics/tracking | None | Google Analytics, etc. |

## For Developers

**Log location**: `backend/data/questions_anonymous.jsonl`

**Log format**: One JSON object per line (JSONL)

**Accessing logs**:
```bash
cat backend/data/questions_anonymous.jsonl | jq '.question'
```

**Privacy considerations when extending**:
- Never add user_id or session_id to logs
- Avoid timestamp precision beyond minute-level
- Do not correlate questions within a session
- Review any new data collection through privacy lens
