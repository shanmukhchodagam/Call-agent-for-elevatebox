# Elevate Sales Agent

An autonomous AI sales qualification, real-time mid-call execution, and post-call intelligence agent built for **ElevateBox** (an e-commerce website development agency).

The system seamlessly combines **in-call tool calling** (dispatching digital assets to callers over WhatsApp while the conversation is live) with **deep post-call intelligence** (deterministic numerical parsing, grounded Gemini LLM semantic extraction, indirect intent reading, barrier tracking, callback scheduling, and SQLite persistence).

```
DIAL ──► SPEAK ──► MID-CALL ACTION ──► DISCOVER ──► UNDERSTAND ──► CLASSIFY ──► ACT ──► SCHEDULE ──► FOLLOW UP
```

---

## Architecture Overview

```
                                      +-----------------------------------------+
                                      |     OmniDimension Voice Platform        |
                                      |   (Telephony, Streaming ASR & TTS)      |
                                      +--------------------+--------------------+
                                                           |
                      +────────────────────────────────────┴────────────────────────────────────+
                      | Live In-Call Custom Tool Trigger                                       | Post-Call Transcript Ingestion
                      v                                                                        v
   +--------------------------------------+                                 +-------------------------------------+
   |      app/server.py (Mid-Call Webhook)|                                 |        app/conversation/parser      |
   |  - Listens: POST /webhook/in-call-act|                                 |  - Isolates customer statements     |
   |  - Dispatches WhatsApp mid-call      |                                 |  - Prevents bot assumption leak     |
   |  - Returns spoken confirmation to bot|                                 +------------------+------------------+
   +------------------+-------------------+                                                    |
                      |                                                                        v
                      |                                                     +-------------------------------------+
                      |                                                     |        app/intelligence/            |
                      |                                                     |  ├── understand.py (Regex/Ranges)   |
                      |                                                     |  ├── semantic.py (Gemini 2.5 Flash) |
                      |                                                     |  └── classifier.py (Intent & State) |
                      |                                                     +------------------+------------------+
                      |                                                                        |
                      |                                          +─────────────────────────────+─────────────────────────────+
                      |                                          v                             v                             v
                      |                             +-------------------------+   +-------------------------+   +-------------------------+
                      |                             |     app/scheduling      |   |       app/actions       |   |      app/followup       |
                      |                             |  - CallbackScheduler    |   |   - WhatsAppService     |   |   - FollowupService     |
                      |                             |  - Timezone-aware ISO   |   |   - Safe mock fallback  |   |   - Section 06 payloads |
                      |                             +------------+------------+   +------------+------------+   +------------+------------+
                      |                                          |                             |                             |
                      +──────────────────────────────────────────┴─────────────────────────────┴─────────────────────────────+
                                                                 |
                                                                 v
                                            +-----------------------------------------+
                                            |              app/database               |
                                            |  - SQLite Engine (elevate_sales.db)     |
                                            |  - Leads, Callbacks, Followup Records   |
                                            +-----------------------------------------+
```

---

## Core Capabilities

### 1. Mid-Call Real-Time Interaction (`app/server.py` + `scripts/setup_midcall_tool.py`)
- Real-time tool execution during active phone conversations.
- When a caller says *"can you send me the details?"* or asks for package pricing, OmniDimension triggers our webhook (`POST /webhook/in-call-action`).
- The server dispatches the portfolio and pricing packages to the customer's WhatsApp in real time.
- Returns a confirmation payload to the voice agent:
  > *"I've just sent the details to your WhatsApp right now, you should see them on your screen."*
- Enables conversational continuity where the prospect can review details while still on the line.

### 2. "The Action is the Point, Not the Label" — Indirect Human Intent Handling
Real customers rarely say *"I am a hot lead."* Instead, they say:
- *"Send me the details"* or *"How soon can you start?"*
- *"My budget is not much right now"* or *"My brother handles this"*
- *"Not interested"* or *"I'm just browsing"*

Our classification engine (`app/intelligence/classifier.py`) evaluates indirect intent and maps it to three operational states and three distinct business actions:

| State | Observable Human Cue / Signal | Action | Next Step Triggered |
| :--- | :--- | :--- | :--- |
| **`HOT`** | `"send me the details"`, `"how soon can you start"`, budget >= 50k, timeline <= 2 mos | `fire_whatsapp_midcall` | Dispatches portfolio & pricing packages mid-call or immediately post-call. |
| **`WARM`** | `"my budget is tight"`, `"my brother handles this"`, flexible timeline | `capture_barrier_and_schedule_callback` | Identifies specific friction (`budget_constraint`, `stakeholder_dependency`), logs barrier, and schedules callback. |
| **`COLD`** | `"not interested"`, single-word answers, no budget or requirements | `log_and_send_overview` | Logs conversation context in SQLite; queues light overview without high-touch follow-up. |

### 3. Customer Statement Isolation (Zero Hallucination / Level 4 Ambiguity)
- Disentangles agent questions from customer responses using `app/conversation/parser.py`.
- Solves the common **Level 4** ambiguity trap:
  - If the customer says *"I ran a closing business"* (ASR transcription error) and the bot responds *"So you sell clothing items"*, our system does **not** hallucinate clothing as confirmed fact.
  - The unconfirmed assumption is isolated under `inferred_business_type: "clothing (unconfirmed)"`, keeping verified `business_type: null`.

### 4. Hybrid Extraction Engine (`app/intelligence`)
- **Deterministic Regex Extraction (`understand.py`)**: High-accuracy numerical and colloquial range parser:
  - Products: `"around 500 to 600"`, `"500-600 products"`, `"between 100 and 200 items"`, `"five hundred"`.
  - Budget: `"50 to 60 thousand"`, `"50k - 60k"`, `"around 50k"`, `"Rs. 50,000 to Rs. 60,000"`, `"1 to 2 lakhs"`.
  - Timeline: `"in another 2 months"`, `"within 3 months"`, `"two months"`, `"8 weeks"`.
- **Grounded Semantic Extractor (`semantic.py`)**: Powered by Google Gemini (`gemini-2.5-flash`) with structured schema constraints, automatic retry logic, and safe fallback.

### 5. Section 06 Assignment Grounded Follow-Up
- Adheres strictly to Section 06 requirements.
- Generates transparent, grounded follow-ups incorporating:
  - Candidate contact information (`+919381758441`)
  - Evaluator destination (`+918688664337`)
  - Architecture diagram reference
  - Verified customer specifications (product count, budget, timeline, payment gateway, checkout preferences).

### 6. Timezone-Aware Callback Scheduling (`app/scheduling`)
- Converts colloquial time statements (*"call me tomorrow morning"*, *"call back in 2 hours"*, *"tomorrow at 4 pm"*) into ISO-8601 localized datetimes (`Asia/Kolkata`).
- Persists records into SQLite `callbacks` table.

---

## Directory Structure

```
elevate_sales_agent/
├── app/
│   ├── actions/
│   │   ├── __init__.py
│   │   └── whatsapp.py             # WhatsApp provider boundary with graceful fallback
│   ├── conversation/
│   │   ├── __init__.py
│   │   └── parser.py               # Dialogue turns & customer statement isolation
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py               # LeadRecord, CallbackRecord, FollowupRecord dataclasses
│   │   └── repository.py           # SQLite repository with schema auto-init
│   ├── followup/
│   │   ├── __init__.py
│   │   └── service.py              # Section 06 grounded message generation
│   ├── intelligence/
│   │   ├── __init__.py
│   │   ├── classifier.py           # Rule-based qualification & indirect cue reader
│   │   ├── semantic.py             # Grounded Gemini GenAI semantic parser
│   │   └── understand.py           # Deterministic regex range extraction
│   ├── scheduling/
│   │   ├── __init__.py
│   │   └── callback.py             # Relative datetime parsing (Asia/Kolkata)
│   ├── telephony/
│   │   ├── __init__.py
│   │   └── service.py              # OmniDimension telephony client wrapper
│   ├── config.py                   # Centralized environment configurations
│   ├── main.py                     # CLI & orchestrator for live / offline processing
│   ├── server.py                   # Mid-call webhook server for OmniDimension tool calls
│   └── __init__.py
├── scripts/
│   ├── setup_midcall_tool.py       # Attaches custom WhatsApp tool to OmniDimension agent
│   ├── sample_call.json            # Reference call transcript & interaction log (Call 8605274)
│   ├── extract_call.py             # Fetches and inspects live call logs from OmniDimension
│   ├── trigger_call.py             # Dispatches live outbound test calls
│   └── configure_discovery.py      # Updates discovery behavior on OmniDimension agent
├── tests/
│   ├── test_callback.py            # Unit tests for relative datetime parsing
│   ├── test_classifier.py          # Unit tests for scoring & indirect intent reading
│   ├── test_conversation_parser.py # Tests for customer statement isolation & turn sequencing
│   ├── test_database.py           # SQLite persistence, queries, and upsert tests
│   ├── test_e2e_pipeline.py        # End-to-end integration tests (Call 8605274 & callbacks)
│   ├── test_followup.py            # Section 06 grounded message tests
│   ├── test_semantic.py            # Gemini semantic extraction & retry tests
│   ├── test_server.py              # Mid-call webhook server tests
│   ├── test_understand.py          # Deterministic regex & range extraction tests
│   └── test_whatsapp.py            # WhatsApp provider boundary tests
├── .env.example                    # Environment variable template
├── .gitignore                      # Git ignore rules (secrets, sqlite db, caches)
├── requirements.txt                # Pinned project dependencies
└── README.md
```

---

## Setup & Installation

### 1. Prerequisites
- Python 3.10 or higher
- Conda or virtual environment (recommended):
  ```bash
  conda create -n elevate-agent python=3.10 -y
  conda activate elevate-agent
  ```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your API credentials:
```bash
cp .env.example .env
```

`.env` configuration details:
```ini
# OmniDimension Voice AI Credentials
OMNIDIM_API_KEY=your_omnidimension_api_key_here
OMNIDIM_AGENT_ID=259394

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# SQLite Database & System Settings
DATABASE_PATH=elevate_sales.db
TIMEZONE=Asia/Kolkata

# Candidate & Evaluator Settings (Section 06 Requirements)
CANDIDATE_MOBILE_NUMBER=+919381758441
ARCHITECTURE_IMAGE_URL=https://raw.githubusercontent.com/elevate_sales_agent/main/architecture.png
EVALUATOR_PHONE_NUMBER=+918688664337

# WhatsApp Action Provider (Optional)
# If left blank, actions are safely recorded to SQLite without failing
WHATSAPP_API_KEY=
WHATSAPP_PHONE_NUMBER_ID=
```

---

## Running the Application

### 1. Real-Time Mid-Call Interaction Flow

To enable the agent to trigger WhatsApp actions *while the call is in progress*:

1. **Start the Webhook Server**:
   ```bash
   python -m app.server
   ```
   *Runs by default on `http://0.0.0.0:8000` with endpoint `/webhook/in-call-action`.*

2. **Expose the Webhook via Tunnel (e.g. ngrok)**:
   ```bash
   ngrok http 8000
   ```
   *Copy your forwarding URL (e.g., `https://abc1234.ngrok-free.app`).*

3. **Register the Custom API Tool to your OmniDimension Agent**:
   ```bash
   python scripts/setup_midcall_tool.py --url https://abc1234.ngrok-free.app/webhook/in-call-action
   ```

4. **Live Call Execution**:
   - When the user asks for pricing or details during the call, OmniDimension invokes the tool.
   - The server dispatches the WhatsApp package message immediately and informs the bot.
   - The bot speaks: *"I've just sent the details to your WhatsApp right now, you should see them on your screen."*

---

### 2. Offline / Evaluation Pipeline Harness (`process-file`)

Process any saved call log JSON (such as the provided `scripts/sample_call.json` representing live Call ID 8605274) without external telephony calls:

```bash
python -m app.main process-file --path scripts/sample_call.json
```

**Output**:
- Complete pipeline run logging:
  - Step 1: Discover & turn parsing
  - Step 2: Deterministic & semantic understanding
  - Step 3: Qualification & scoring (HOT / WARM / COLD)
  - Step 4: Callback scheduling detection
  - Step 5: Real-time action trigger
  - Step 6: Follow-up message generation
  - Step 7: SQLite persistence

---

### 3. Live Telephony Processing (`process`)

Process a completed call directly from OmniDimension via its Call ID:
```bash
python -m app.main process --call-id 8605274
```

---

### 4. Dispatch an Outbound Sales Call (`dial`)

Initiate an automated outbound discovery call to a prospect:
```bash
python -m app.main dial --phone +919381758441
```

---

### 5. Inspect Database Records

Query saved leads, scores, and qualification tiers directly from the CLI:
```bash
# List all processed leads
python -m app.main list-leads

# Get complete details for a specific call
python -m app.main get-lead --call-id 8605274
```

---

## Test Suite & Validation

The test suite contains **52 unit and integration tests** covering all parsing, classification, database, action, and server endpoints.

Run the entire suite:
```bash
python -m unittest discover tests
```

### Running Individual Test Suites:
```bash
# Regex & range parsing
python -m unittest tests/test_understand.py

# Customer statement isolation & turn sequencing
python -m unittest tests/test_conversation_parser.py

# Intent scoring, barriers, and state classification
python -m unittest tests/test_classifier.py

# Timezone-aware callback resolution
python -m unittest tests/test_callback.py

# Section 06 grounded follow-up generation
python -m unittest tests/test_followup.py

# SQLite repository and persistence
python -m unittest tests/test_database.py

# Mid-call webhook server
python -m unittest tests/test_server.py

# WhatsApp provider boundary
python -m unittest tests/test_whatsapp.py

# Gemini semantic extractor
python -m unittest tests/test_semantic.py

# Full end-to-end integration pipeline
python -m unittest tests/test_e2e_pipeline.py
```

---

## Lead Qualification Matrix & Scoring

Scoring is deterministic and transparent:

| Signal | Evaluation Condition | Points |
| :--- | :--- | :--- |
| **Budget Scale** | >= Rs. 50,000<br>Rs. 20,000 – 49,999<br>< Rs. 20,000 | +25 pts<br>+15 pts<br>+10 pts |
| **Timeline Urgency** | <= 2 months<br>3 – 6 months<br>> 6 months | +25 pts<br>+15 pts<br>+5 pts |
| **Catalog Scope** | >= 500 products<br>50 – 499 products<br>< 50 products | +20 pts<br>+15 pts<br>+10 pts |
| **Payment Gateway** | Explicitly requested | +10 pts |
| **Checkout Mode** | Preference specified (e.g. Guest Checkout) | +10 pts |
| **Business Domain** | Domain stated by customer | +10 pts |
| **Custom Requirements** | Additional notes provided | +5 pts |

### Qualification Tiers:
- **`HOT` (Score >= 70)**: High urgency, substantial budget, defined scope. Action: `fire_whatsapp_midcall`.
- **`WARM` (Score 40–69)**: Qualified requirement with friction or flexible timeline. Action: `capture_barrier_and_schedule_callback`.
- **`COLD` (Score < 40)**: Minimal qualification signals or disengaged. Action: `log_and_send_overview`.

---

## Design Highlights & Engineering Decisions

1. **Deterministic-First Architecture**: Numerical quantities, budgets, and timelines are parsed with deterministic regex before calling LLMs. This prevents hallucinated ranges while maintaining speed and reproducibility.
2. **Graceful Action Degradation**: The WhatsApp action boundary does not throw unhandled exceptions or fake delivery if credentials are not configured. It logs `status: provider_not_configured`, stores the drafted message in SQLite, and prints it cleanly for review.
3. **Reproducibility**: All external integrations (OmniDimension, Gemini, WhatsApp) have mocked offline test harnesses ensuring that anyone cloning this repository can run `python -m unittest discover tests` without requiring paid third-party API keys.
