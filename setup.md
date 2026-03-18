# ImmersiveRAG — Company Setup Guide

> This guide covers cloning the repo, configuring your company's embedding and LLM API keys, and running the full stack locally on a Windows machine.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://python.org) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Git | any | [git-scm.com](https://git-scm.com) |
| VS Code (recommended) | any | [code.visualstudio.com](https://code.visualstudio.com) |

---

## Step 1 — Clone the Repository

```powershell
# Clone from your company's GitHub
git clone https://github.com/<your-org>/ImmersiveRAG.git
cd ImmersiveRAG
```

---

## Step 2 — Backend Setup

### 2a. Create the Python Virtual Environment

```powershell
cd backend

# Create venv using Python 3.11+
python -m venv .venv

# Activate
.venv\Scripts\Activate.ps1
```

> If you get a script execution policy error, run:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 2b. Install Dependencies

```powershell
# Install all declared packages from pyproject.toml
pip install -e .

# Also install these two runtime dependencies explicitly
pip install aiofiles PyPDF2
```

### 2c. Configure Environment Variables

Create a `.env` file inside the `backend/` folder:

```powershell
New-Item -Path "backend\.env" -ItemType File
```

Open it and add your **company-provided** API credentials:

```env
# ── Company Embedding API (OpenAI-compatible) ──────────────────────────────
IMMERSIVE_RAG_OPENAI_API_KEY=your-company-embedding-api-key-here
IMMERSIVE_RAG_OPENAI_BASE_URL=https://your-company-api-gateway.example.com/v1
IMMERSIVE_RAG_EMBEDDING_MODEL=text-embedding-3-small

# ── Company LLM Reasoning API (Generation Model) ──────────────────────────
# Used if you extend the agent to generate answers (not just retrieve chunks)
IMMERSIVE_RAG_LLM_API_KEY=your-company-llm-api-key-here
IMMERSIVE_RAG_LLM_BASE_URL=https://your-company-api-gateway.example.com/v1
IMMERSIVE_RAG_LLM_MODEL=gpt-4o

# ── Optional: LlamaParse Cloud (for high-fidelity PDF extraction) ──────────
IMMERSIVE_RAG_LLAMA_PARSE_API_KEY=your-llamaparse-key-here
```

> **Note:** If `IMMERSIVE_RAG_OPENAI_API_KEY` is not set, the system automatically falls back to **local FastEmbed** (384-dim, no key needed). This is safe for initial testing.

---

## Step 3 — Frontend Setup

```powershell
cd ..\frontend

# Install Node dependencies
npm install
```

No `.env` file is needed for the frontend — the Next.js proxy rewrites all `/api/*` calls to `http://127.0.0.1:8000` automatically via `next.config.ts`.

---

## Step 4 — Run the Stack

Open **two separate PowerShell terminals**:

### Terminal 1 — Start the Backend

```powershell
cd e:\<your-path>\ImmersiveRAG\backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

✅ Wait for: `INFO: Application startup complete.`

### Terminal 2 — Start the Frontend

```powershell
cd e:\<your-path>\ImmersiveRAG\frontend
$env:PATH += ";C:\Program Files\nodejs"   # only needed if node isn't on PATH
npm run dev -- -p 3000
```

✅ Wait for: `▲ Next.js ... ✓ Ready in ~2s`

---

## Step 5 — Access the Application

| Service | URL |
|---------|-----|
| **Dashboard UI** | http://localhost:3000 |
| **Swagger API Docs** | http://127.0.0.1:8000/docs |

---

## Step 6 — Choosing Ingestion Mode

When you open the dashboard, you'll see two configuration panels:

### Extraction Provider
| Option | When to Use |
|--------|-------------|
| **Local Fallback** | Default — uses PyPDF2 (PDF) or plain text read. No API key needed. Works offline. |
| **LlamaParse (Cloud)** | High-fidelity Markdown extraction. Requires `IMMERSIVE_RAG_LLAMA_PARSE_API_KEY`. |

### Vector Embedding Strategy
| Option | When to Use |
|--------|-------------|
| **FastEmbed (Local)** | Default — 384-dim local model. Zero latency. No API key needed. |
| **OpenAI (Corporate API)** | 1536-dim company embedding model. Requires `IMMERSIVE_RAG_OPENAI_API_KEY` and `IMMERSIVE_RAG_OPENAI_BASE_URL`. |

> ⚠️ Do not mix embedding modes across uploads. If you re-ingest with a different mode, purge first: `DELETE /admin/debug/purge-vectors` in Swagger.

---

## Step 7 — Upload and Test

1. Select your preferred modes (Local Fallback + FastEmbed for first test)
2. Drag and drop a `.pdf` or `.txt` file onto the upload zone
3. Watch the status: `processing` → `embedding_and_indexing` → **Complete ✅**
4. In the right panel, type a question about your document
5. The agent returns matching paragraph-level chunks with similarity scores

---

## Resetting the Vector Store

If you need a clean slate (after a bad ingestion run, or when switching embedding providers):

```
DELETE http://127.0.0.1:8000/admin/debug/purge-vectors
```

Or from Swagger UI: `DELETE /admin/debug/purge-vectors` → Try it out → Execute.

This deletes all vectors from Qdrant and clears the SQLite job history.

---

## Gitignore Checklist

Ensure these are in your `.gitignore` before pushing:

```gitignore
# Python
backend/.venv/
backend/__pycache__/
backend/**/__pycache__/

# Runtime data
backend/data/
backend/.env

# Node
frontend/node_modules/
frontend/.next/

# Misc
*.pyc
.DS_Store
```

---

## Common Errors

| Error | Fix |
|-------|-----|
| `No module named 'aiofiles'` | Run: `pip install aiofiles PyPDF2` in the backend `.venv` |
| `Collection rag_text not found` | Restart backend — it auto-creates collections on startup |
| Chat shows `Error: Could not connect to backend` | Make sure backend is running on port 8000 |
| Upload stuck at `embedding_and_indexing` | APScheduler polls every 5s — wait 10s. If stuck, restart backend |
| `fdprocessedid` hydration warning | Harmless — caused by browser password manager extensions |
| Vectors found but no query match | Chunk too large — ensure you are on the latest `chunker.py`. Purge and re-ingest |
| `OpenAI API error` with company key | Verify `IMMERSIVE_RAG_OPENAI_BASE_URL` ends with `/v1` and key is correct |

---

## Architecture Overview (Quick Reference)

```
Browser (localhost:3000)
      │ /api/* (Next.js proxy rewrite)
      ▼
FastAPI (127.0.0.1:8000)
  ├── POST /admin/ingest        → pipeline.py → chunker.py → SQLite
  ├── APScheduler (every 5s)   → embedder.py → Qdrant
  ├── POST /agent/query         → orchestrator.py → session_cache → Qdrant
  └── GET  /admin/debug/*       → inspection endpoints

Storage
  ├── data/rag.db              SQLite (jobs, sessions, cache)
  └── data/qdrant/             Local Qdrant vector store (on-disk, 384 or 1536-dim)
```
