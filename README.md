# magicpin AI Challenge — Vera Assistant

Production-grade implementation of **Vera**, magicpin's merchant AI assistant for WhatsApp local commerce engagement.

---

## 1. Overview

Vera engages local merchants and customers across India (dentists, salons, restaurants, gyms, pharmacies) over WhatsApp by combining four distinct context layers:

```
compose(CategoryContext, MerchantContext, TriggerContext, CustomerContext?) -> ComposedMessage
```

Key capabilities:
- **100% Fact-Grounded**: Zero hallucination of discounts, competitor stats, appointment times, or research citations. Uses only verifiable facts from the provided contexts.
- **Category Voice Alignment**: Clinical-peer tone for dentists (no medical overclaims), warm fellow-operator register for salons and restaurants, motivational coaching for gyms, and trustworthy precision for pharmacies.
- **Stateful Multi-Turn Turn Handling**:
  - **Auto-Reply Loop Detection**: Detects canned WhatsApp Business automated replies and repetitive loops; pauses with a `wait` action and exits gracefully after repeated attempts.
  - **Instant Intent Transition**: Immediately switches from qualifying questions to concrete execution actions when a merchant commits ("Ok let's do it", "send the abstract", "proceed").
  - **Hostility & Opt-Out Handling**: Honors opt-out requests with immediate `action: "end"` and stops outreach.
  - **Off-Topic Redirection**: Politely deflects out-of-scope requests (e.g. GST filing) while steering back to core business goals.
- **Deterministic by Default**: Runs entirely without requiring external LLM API keys. An isolated LLM adapter is available via `USE_LLM=true` with instant fallback.

---

## 2. Architecture

```
                      HTTP / JSON (FastAPI)
                                │
                       [Context Store]
          (Thread-safe In-Memory Store & State Tracker)
                                │
                   [4-Context Normalization]
     (CategoryContext, MerchantContext, TriggerContext, CustomerContext)
                                │
                     [Intent & Scope Router]
                                │
       ┌────────────────────────┴────────────────────────┐
       ▼                                                 ▼
[Deterministic Domain Handlers]               [Fallback Composer]
(26 specialized trigger kinds)              (Unseen triggers & categories)
       │                                                 │
       └────────────────────────┬────────────────────────┘
                                ▼
                    [Safety & Fact Validator]
       (Stripping unapproved URLs, sanitizing taboo terms)
                                ▼
                       Composed Response
```

---

## 3. Project Structure

```
magicpin-vera/
├── app/
│   ├── config.py                 # Environment and application settings
│   ├── main.py                   # FastAPI server exposing the 5 challenge endpoints
│   ├── models/
│   │   ├── schemas.py            # Pydantic request/response schemas
│   │   └── domain.py             # 4-Context dataclasses and normalization helpers
│   ├── storage/
│   │   └── context_store.py      # Versioned idempotent context & conversation store
│   ├── composer/
│   │   ├── base.py               # Abstract composer interface
│   │   ├── deterministic.py      # Fact-grounded domain composition handlers
│   │   ├── fallback.py           # Robust generalized fallback composer
│   │   ├── llm_adapter.py        # Isolated LLM adapter (optional)
│   │   └── engine.py             # Master composition orchestrator
│   ├── multi_turn/
│   │   ├── auto_reply_detector.py # Canned and verbatim auto-reply detector
│   │   ├── intent_classifier.py  # Intent classifier (commitment, hostile, wait, etc.)
│   │   └── reply_handler.py      # Turn response generator (send, wait, end)
│   └── validator/
│       └── safety.py             # Safety sanitization (URLs, taboo terms, field validation)
├── dataset/
│   ├── categories/               # 5 vertical seed files (dentists, salons, etc.)
│   ├── merchants_seed.json       # Representative merchant seeds
│   ├── customers_seed.json       # Representative customer seeds
│   ├── triggers_seed.json        # Representative trigger seeds
│   ├── generate_dataset.py       # Reproducible dataset expander
│   └── expanded/                 # Expanded 50 merchants, 200 customers, 100 triggers
├── tests/
│   ├── test_health_metadata.py   # Healthz and metadata endpoint tests
│   ├── test_context_ingestion.py # Context ingestion, idempotency, versioning tests
│   ├── test_tick.py              # Proactive tick generation & deduplication tests
│   ├── test_reply.py             # Turn handling (auto-reply, intent transition, hostility)
│   ├── test_canonical_pairs.py   # Verification of all 30 canonical test cases
│   └── test_robustness.py        # Missing fields, unseen triggers, teardown tests
├── bot.py                        # Standalone challenge entrypoint (compose & app export)
├── generate_submission.py        # Generates official submission.jsonl
├── submission.jsonl              # 30 canonical test pair outputs
├── judge_simulator.py            # Official challenge test harness
├── requirements.txt              # Production runtime dependencies
├── Dockerfile                    # Container definition
├── Procfile                      # Cloud platform process file
└── .env.example                  # Environment configuration template
```

---

## 4. API Endpoints

The service strictly implements the HTTP contract specified in `challenge-testing-brief.md`:

| Endpoint | Method | Description |
|---|---|---|
| `/v1/healthz` | GET | Liveness probe returning status, uptime, and loaded context counts. |
| `/v1/metadata` | GET | Metadata returning team name, model, approach, version, and contact. |
| `/v1/context` | POST | Receive context push (category, merchant, customer, trigger). Idempotent on `(context_id, version)`. Returns 409 on stale version conflict. |
| `/v1/tick` | POST | Periodic simulated time wake-up. Inspects active triggers and returns proactive message actions. |
| `/v1/reply` | POST | Handles incoming merchant or customer replies. Returns `send`, `wait`, or `end`. |
| `/v1/teardown` | POST | Optional maintenance hook to wipe state between test runs. |

---

## 5. Local Setup & Execution

### Prerequisites
- Python 3.10+
- pip

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Generate Expanded Dataset
```bash
python dataset/generate_dataset.py --seed-dir ./dataset --out ./dataset/expanded
```

### Run Tests
```bash
pytest -q
```

### Generate Submission File
```bash
python generate_submission.py
```
This produces `submission.jsonl` with all 30 canonical outputs.

### Start Server Locally
```bash
python -m uvicorn bot:app --host 0.0.0.0 --port 8080
```

Verify endpoints:
```bash
curl http://localhost:8080/v1/healthz
curl http://localhost:8080/v1/metadata
```

---

## 6. Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `HOST` | `0.0.0.0` | Server bind interface |
| `PORT` | `8080` | Server listen port (respects cloud-injected `$PORT`) |
| `TEAM_NAME` | `magicpin-challenge-candidate` | Team name in metadata |
| `CONTACT_EMAIL` | `candidate@example.com` | Contact email in metadata |
| `USE_LLM` | `false` | Enable external LLM (disabled by default for determinism) |
| `OPENAI_API_KEY` | `""` | Optional LLM API key |
| `PRELOAD_DATASET`| `false` | Preload dataset on startup (keep false for clean judge warmup) |

---

## 7. Deployment Instructions

The application is fully containerized and deployable to any cloud platform exposing a public HTTPS URL.

### Option A — Render / Railway / Fly.io
1. Connect this repository to your platform.
2. The platform automatically detects `Procfile` or `Dockerfile`.
3. Set environment variable `PORT` (assigned automatically by most platforms).
4. Deploy. The health check URL is `https://<your-service-domain>/v1/healthz`.

### Option B — Docker Container
```bash
docker build -t magicpin-vera .
docker run -d -p 8080:8080 -e PORT=8080 magicpin-vera
```

---

## 8. Verification & Test Results

- **20 / 20 unit and integration tests passing** covering all functional areas.
- **30 / 30 canonical test pairs verified**:
  - No raw URLs in message bodies.
  - Zero category taboo terms.
  - Correct `send_as` attribution (`vera` for merchant scope, `merchant_on_behalf` for customer scope).
  - All required fields present (`body`, `cta`, `send_as`, `suppression_key`, `rationale`).
