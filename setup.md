# ImmersiveRAG — Setup & Deployment Guide

> Full-stack RAG + Multi-Agent AI platform. Runs entirely locally.  
> **Stack**: FastAPI + LangGraph + Qdrant + Next.js 16

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.11+ | [python.org](https://python.org) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Git | any | [git-scm.com](https://git-scm.com) |

---

## Architecture

```
Browser (localhost:3000)
      │  /api/* → Next.js proxy rewrite
      ▼
FastAPI (127.0.0.1:8000)
  ├── POST /admin/ingest          Ingestion pipeline → SQLite job queue
  ├── APScheduler (every 5s)     embedder.py → Qdrant vector store
  ├── POST /agent/chat/stream     SSE Streaming: retrieve → re-rank → generate (Groq/OpenAI)
  ├── GET  /agent/registry        Lists base + user-configured agents
  ├── POST /agent/configure       Clone & customize agents (saved to SQLite)
  └── DELETE /admin/debug/purge-vectors   Full wipe (Qdrant + SQLite)

LangGraph Workflow (per chat message)
  retrieve node → Chunk Retrieval → Cross-Encoder Re-ranker (top-5)
  generate node → StreamingResponse (SSE) → LLM answer tokens

Memory (3 tiers)
  T1: session_context_cache   Turn-level dedup (SQLite)
  T2: conversation_messages   Full message log (SQLite)
  T3: agent_sessions.summary  Rolling digest, refreshed every 4 turns

Storage
  backend/data/rag.db           SQLite (jobs, sessions, agents, cache, messages)
  backend/data/qdrant/          On-disk Qdrant (384-dim FastEmbed or 1536-dim OpenAI)
```

---

## Step 1 — Clone

```powershell
git clone https://github.com/<your-org>/ImmersiveRAG.git
cd ImmersiveRAG
```

---

## Step 2 — Backend Setup

### 2a. Create Virtual Environment

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> If you get a script policy error:  
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 2b. Install Dependencies

```powershell
pip install -r requirements.txt
```

> **Note:** First run downloads the FastEmbed model (~130 MB). This is automatic.

### 2c. Configure Environment Variables

```powershell
copy .env.example .env
```

Open `.env` and fill in your credentials:

```env
# Required for LLM generation (Groq example — free at console.groq.com)
IMMERSIVE_RAG_LLM_API_KEY=gsk_your_groq_key_here
IMMERSIVE_RAG_LLM_BASE_URL=https://api.groq.com/openai/v1
IMMERSIVE_RAG_LLM_MODEL=llama-3.3-70b-versatile

# Optional: Corporate embedding API (falls back to FastEmbed if unset)
IMMERSIVE_RAG_OPENAI_API_KEY=
IMMERSIVE_RAG_OPENAI_BASE_URL=
IMMERSIVE_RAG_EMBEDDING_MODEL=text-embedding-3-small

# Optional: LlamaParse cloud PDF extraction
IMMERSIVE_RAG_LLAMA_PARSE_API_KEY=
```

> **Supported LLM providers** (all OpenAI-compatible):
> | Provider | BASE_URL | Example Model |
> |---|---|---|
> | **Groq** (recommended, free) | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
> | **OpenAI** | `https://api.openai.com/v1` | `gpt-4o` |
> | **Azure OpenAI** | `https://<resource>.openai.azure.com/openai/deployments/<model>` | `gpt-4o` |

---

## Step 3 — Frontend Setup

```powershell
cd ..\frontend
npm install
```

No `.env` file needed — Next.js proxies all `/api/*` calls to `http://127.0.0.1:8000` automatically via `next.config.ts`.

---

## Step 4 — Run the Stack

Open **two PowerShell terminals**:

**Terminal 1 — Backend**
```powershell
cd ImmersiveRAG\backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
✅ Wait for: `INFO: Application startup complete.`

**Terminal 2 — Frontend**
```powershell
cd ImmersiveRAG\frontend
npm run dev
```
✅ Wait for: `▲ Next.js ... ✓ Ready`

---

## Step 5 — Access

| Service | URL |
|---|---|
| **Dashboard UI** | http://localhost:3000 |
| **Swagger API Docs** | http://127.0.0.1:8000/docs |

---

## Step 6 — Using the Application

### Upload Documents
1. Right panel → drag-and-drop a `.pdf` or `.txt`
2. Choose: **Extraction** (Local Fallback or LlamaParse) and **Embedding** (FastEmbed or Corporate API)
3. Status → `queued → processing → embedding_and_indexing → Complete ✅`

> ⚠️ Don't mix embedding modes. If you switch, purge first (see below).

### Chat with Agents
1. **Select an agent** from the top-left dropdown (Document Analyzer or General Assistant)
2. Type your question — the agent retrieves context from Qdrant and generates an answer via Groq
3. Click **Sources (N)** below each answer to see the matched document chunks

### Configure Custom Agents
1. Open the dropdown → **Configure New Agent**
2. Choose a base agent, set a name and custom system prompt
3. Your agent is saved and immediately available in the dropdown

---

## Resetting the Vector Store

```
DELETE http://127.0.0.1:8000/admin/debug/purge-vectors
```
Or via Swagger: `DELETE /admin/debug/purge-vectors → Try it out → Execute`

This physically deletes the Qdrant data directory and clears all SQLite state (jobs, sessions, caches, conversation history). Use before switching embedding modes.

---

## Ingestion Mode Reference

| Mode | Description | Requires |
|---|---|---|
| Local Fallback (extraction) | PyPDF2 / plain text | Nothing |
| LlamaParse (extraction) | High-fidelity Markdown | `IMMERSIVE_RAG_LLAMA_PARSE_API_KEY` |
| FastEmbed (embedding) | 384-dim local model | Nothing |
| Corporate API (embedding) | 1536-dim OpenAI-compat | `IMMERSIVE_RAG_OPENAI_API_KEY` + `IMMERSIVE_RAG_OPENAI_BASE_URL` |

---

## Common Errors

| Error | Fix |
|---|---|
| `IMMERSIVE_RAG_LLM_API_KEY is not set` | Add your Groq/OpenAI key to `backend/.env` |
| `Collection rag_text not found` | Restart backend — collections are auto-created on startup |
| Chat returns `System Error: ...` | Check backend terminal for traceback; verify LLM key is valid |
| Upload stuck at `embedding_and_indexing` | APScheduler polls every 5s — wait 10s. Restart backend if stuck |
| Vectors found but no match | Purge and re-ingest; ensure embedding mode hasn't changed |
| `fdprocessedid` hydration warning | Harmless — caused by browser extension |
| `OpenAI API error` with corporate key | Verify `BASE_URL` ends with `/v1` and key is correct |
| `summary_digest` column error | Restart backend — auto-migration runs on startup |

---

## Project Structure

```
ImmersiveRAG/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── admin_router.py      Ingestion, purge, debug endpoints
│   │   │   └── agent_router.py      Chat, registry, configure endpoints
│   │   ├── core/
│   │   │   ├── config.py            AppConfig (pydantic-settings)
│   │   │   └── scheduler.py         APScheduler background jobs
│   │   ├── engine/
│   │   │   ├── agents/
│   │   │   │   ├── graph_runner.py  LangGraph 2-node workflow
│   │   │   │   ├── llm_client.py    ChatOpenAI singleton (Groq/Azure/OpenAI)
│   │   │   │   └── conversation_memory.py  3-tier memory manager
│   │   │   ├── ingestion/           parser, chunker, embedder, pipeline
│   │   │   ├── retrieval/           orchestrator, session_cache
│   │   │   └── memory/              (future expansion)
│   │   ├── models/
│   │   │   ├── api_models.py        Pydantic request/response schemas
│   │   │   └── domain_models.py     Internal domain models
│   │   ├── storage/
│   │   │   ├── relations_db.py      SQLite init, schema, migrations
│   │   │   └── vector_db.py         Qdrant client singleton + reset
│   │   └── main.py                  FastAPI app factory
│   ├── data/                        ← gitignored (auto-generated)
│   │   ├── rag.db                   SQLite database
│   │   └── qdrant/                  On-disk vector store
│   ├── .env                         ← gitignored (your secrets)
│   ├── .env.example                 Template for new deployments
│   └── requirements.txt             Python dependencies
│
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx             Root page — agent state management
    │   │   └── globals.css          Corporate Luminary design system
    │   ├── components/
    │   │   ├── Navigation/
    │   │   │   ├── Header.tsx       Top bar with PwC logo + theme toggle
    │   │   │   ├── SidebarLeft.tsx  Agent selector dropdown
    │   │   │   └── SidebarRight.tsx Context viewer + document uploader
    │   │   ├── Chat/
    │   │   │   └── AgentChat.tsx    Chat UI with LLM answers + sources
    │   │   └── Agents/
    │   │       └── AgentConfigModal.tsx  Clone + customize agent modal
    │   └── lib/
    │       └── api.ts               Typed API client (all endpoints)
    ├── next.config.ts               /api/* → 127.0.0.1:8000 proxy
    └── package.json
```
