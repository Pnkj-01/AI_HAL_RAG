# sub02: Safety Guardrails & Model Routing

Part of the **AI_hal_rag** framework by Pankaj ([@Pnkj-01](https://github.com/Pnkj-01)).

This module provides input sanitization, dynamic model routing with fallback redundancy, and heuristic output verification to catch and intercept hallucinated or risky responses.

---

## Architecture

```text
User Input
    │
    ▼
[validateInput() / safeQuery()]
    ├── Regex checks (API keys, payment cards, sensitive data)
    └── Max character length verification
    │
    ├── FAIL ──> [logSecurityEvent] ──> [sendToHumanReview] ──> Fallback Safe Message
    │
    └── PASS
         │
         ▼
[queryWithFallbacks()]
    ├── 1. Primary Model: gpt-5.6-terra
    │       └── on failure ──>
    ├── 2. Fallback Model: gpt-5.6-luna
    │       └── on failure ──>
    └── 3. Safe Default Handler
         │
         ▼
[validateOutput()]
    ├── Detects unauthorized legal / medical advice
    ├── Flags long assertions lacking verifiable citations ([...], URL)
    └── Flags statements lacking uncertainty markers
         │
         ├── REJECTED ──> Logged to reviewQueue ──> Safe Default
         └── APPROVED ──> Return Verified Answer
```

---

## Key Features

- **Offline Mock Testing**: `npm test` runs immediately without making paid external API calls by simulating primary model outages and fallback paths.
- **Pre-execution Sanitization**: Intercepts accidental leakage of keys, payment numbers, or malformed queries before sending them to the LLM.
- **Multi-Level Model Redundancy**: If a primary LLM suffers an outage or rate limit, requests automatically cascade to an alternative model without dropping user sessions.
- **Heuristic Output Verification**: Evaluates length, citation patterns, and uncertainty markers to intercept unsupported assertions.
- **In-Memory Telemetry**: Maintains `securityEvents` and `reviewQueue` for auditing and compliance tracking.

---

## Setup & Running

### Prerequisites
- Node.js 20 or newer
- npm

### 1. Install Dependencies
```powershell
npm install
```

### 2. Configure Environment (for live API mode)
```powershell
Copy-Item .env.example .env
```
Inside `.env`:
```dotenv
OPENAI_API_KEY=your-api-key-here
OPENAI_PRIMARY_MODEL=gpt-5.6-terra
OPENAI_FALLBACK_MODEL=gpt-5.6-luna
```

### 3. Run Tests & Demos

Run the offline mocked test (no API charges):
```powershell
npm test
```

Run live against the OpenAI Responses API:
```powershell
npm run start:live
```
