# SecureAI — Privacy-First RAG Prototype

A local-first enterprise RAG system with **sensitive-data masking**, **role-based
access control (RBAC)**, and a **multi-agent query pipeline**. All ingestion,
PII detection, masking, and policy enforcement happen locally — Google Gemini is
the only external dependency and **only ever receives sanitized, policy-approved
context**.

---

## Architecture at a glance

- **Backend** — a FastAPI app (`app/`) exposing `/ingest`, `/chat`, `/admin`,
  `/audit`, and `/health`.
- **Frontend** — a static single-page console (`static/`) served by the *same*
  FastAPI process at `/`. There is no separate frontend server and no build step.
- **Storage** — local SQLite (`data/app.db`) plus an on-disk vector store.
- **LLM** — Google Gemini, used only for final answer composition over masked text.

The query pipeline runs as a chain of agents: intent router → query planner →
prompt guard → retriever → reranker → policy agent → context compressor →
answer composer → answer verifier → redaction agent → audit agent.

---

## Prerequisites

- Python 3.9+
- A Google Gemini API key

---

## Setup

```bash
cd SecureAI

# 1. Create and populate a virtual environment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Download the spaCy NER model used for PII detection
.venv/bin/python -m spacy download en_core_web_sm

# 3. Create your .env from the template and add your Gemini API key
cp .env.example .env
```

Edit `.env` and set at least:

```ini
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.5-flash
```

> The app refuses to start without `GEMINI_API_KEY`. Use a current model name —
> `gemini-2.5-flash` or `gemini-2.0-flash`. Older names like `gemini-1.5-flash`
> are retired and return HTTP 404.

---

## Running the server

The backend **and** frontend are served by one process. From the `SecureAI/`
directory:

```bash
.venv/bin/uvicorn app.main:app --reload --port 8000
```

On first start the app creates `data/app.db`, seeds eight demo users (one per
role), and loads the embedding model — this can take a few seconds.

| URL                              | What it serves                          |
|----------------------------------|------------------------------------------|
| http://localhost:8000            | Frontend console (single-page app)       |
| http://localhost:8000/docs       | Interactive API docs (Swagger UI)        |
| http://localhost:8000/health     | Health check — returns `{"status":"ok"}` |

---

## What the frontend shows

Open http://localhost:8000. The console is a single page with three numbered
sections plus a user switcher:

- **Acting as** (top right) — pick which pre-seeded user you are. Every request
  is made on behalf of this user, which drives RBAC. The user's role is shown
  as a chip beside the dropdown.
- **1 · Ingest a document** — upload a file (`.pdf .docx .txt .html .json`) or
  paste raw text, choose a **sensitivity level** and optional allowed roles, and
  index it. Two one-click sample loaders are provided (HR / Confidential and
  Engineering / Internal). Sensitive values (emails, phone numbers, salaries,
  IDs) are detected and masked locally before anything is stored.
- **2 · Ask a question** — ask a natural-language question about the ingested
  documents. The answer panel shows the composed answer plus metadata: detected
  intent, risk level, sub-queries, injection-guard verdict, per-chunk policy
  decisions, and the verification result. Three preset query chips are provided,
  including a prompt-injection attempt.
- **3 · Audit lookup** — paste a `request_id` (auto-filled from your last query)
  to retrieve the full pipeline trace. **Requires the Admin or Security Analyst
  role** — other users get a 403.

---

## Pre-seeded users

Created automatically on first run. Authenticate API calls with the
`X-User-Id` header (the value is the username below).

| Username         | Role             |
|------------------|------------------|
| `admin`          | Admin            |
| `analyst`        | Security Analyst |
| `hr_user`        | HR               |
| `finance_user`   | Finance          |
| `eng_user`       | Engineering      |
| `manager_user`   | Manager          |
| `employee_user`  | Employee         |
| `guest_user`     | Guest            |

Sensitivity tiers, lowest to highest: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`,
`STRICT_CONFIDENTIAL`.

---

## How to test

### Option A — via the console (recommended)

1. **Ingest** — pick `hr_user` in *Acting as*, then in section 1 click
   *Load HR sample (Confidential)* and press *Ingest document*. Confirm the
   result reports sensitive spans detected and tokens created.
2. **Ask (authorized)** — still as `hr_user`, ask
   *"List the employees in the HR records and their email addresses."*
   You should get an answer; note that masked values are released only because
   HR is authorized for this document.
3. **Ask (RBAC denied)** — switch *Acting as* to `guest_user` and ask the same
   question. The policy agent denies the confidential chunks and the status
   comes back as `no_context`.
4. **Prompt injection** — back as `hr_user`, click the *Injection attempt* chip
   and send it. The injection guard flags it and the answer refuses to unmask.
5. **Audit** — switch to `admin` or `analyst`, paste the `request_id` from a
   previous query into section 3, and press *Fetch trace* to see every agent's
   step. Trying this as `hr_user` returns 403.

### Option B — via the API (curl)

```bash
# Health check
curl http://localhost:8000/health

# Ingest raw text as hr_user
curl -X POST http://localhost:8000/ingest/document \
  -H 'X-User-Id: hr_user' \
  -F 'raw_text=John Smith, john.smith@acme-corp.com, salary $142,000.' \
  -F 'filename=hr.txt' \
  -F 'sensitivity_level=CONFIDENTIAL'

# Ask a question
curl -X POST http://localhost:8000/chat/query \
  -H 'X-User-Id: hr_user' -H 'Content-Type: application/json' \
  -d '{"query":"What is John Smith email?"}'

# Retrieve the audit trace (Admin or Security Analyst only)
curl http://localhost:8000/audit/<request_id> -H 'X-User-Id: analyst'
```

A successful query response includes `status` (`ok`, `redacted`, `no_context`,
or `error`), the composed `answer`, the `injection_guard` verdict, per-chunk
`retrieved_chunks` policy decisions, `verification`, and the full agent `trace`.

### Notes

- Gemini occasionally returns a transient `503 "high demand"` — the query then
  reports `status: error`. Retry, or switch `GEMINI_MODEL` to `gemini-2.0-flash`.
- There is no automated test suite; testing is manual via the console or API.

---

## Project layout

```
SecureAI/
├── app/
│   ├── main.py          # FastAPI entrypoint, user seeding, static mount
│   ├── api/             # Route handlers: ingest, chat, admin, audit
│   ├── agents/          # Multi-agent query pipeline
│   ├── services/        # Ingestion, retrieval, masking, Gemini, embeddings
│   ├── storage/         # SQLite DB, vector store, token store
│   ├── models/          # SQLAlchemy ORM models
│   ├── utils/           # PII detection, chunking, redaction, text extraction
│   └── core/            # Config, constants, security, logging
├── static/              # Frontend console (index.html, app.js, styles.css)
├── samples/             # Sample documents
├── requirements.txt
└── .env                 # Local config (gitignored)
```
