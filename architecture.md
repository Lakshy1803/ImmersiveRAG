# ImmersiveRAG — Architecture & System Design

This document details the internal workings of the ImmersiveRAG platform — the ingestion pipeline, vector storage, agentic reasoning engine, and agent registry.

---

## 1. System Overview

ImmersiveRAG is a decoupled architecture with a **FastAPI** backend and a **Next.js 14** frontend. It is designed **local-first**: it can run entirely on a workstation without cloud dependencies (FastEmbed + no LLM key required for retrieval), while supporting corporate APIs (OpenAI/Groq/LlamaParse). The backend implements the **Phase 1 Agent Builder Platform** from `my_plan.md` — static multi-agent workflows, configurable base agents, a Master Orchestrator, and a tool execution service.

```
User (Browser)
    ↓
Next.js Frontend (Port 3000) — /api/* proxied to backend
    ↓
FastAPI Backend (Port 8000)
    ↓
┌──────────────────────────────────────────────────────┐
│  Admin Router         │  Agent Router                │
│  /admin/*             │  /agent/*                    │
│  - Ingestion          │  - chat (SSE + blocking)     │
│  - LLM Config         │  - agent registry            │
│  - Qdrant stats       │  - export tools              │
│  - Debug              │  - master_workflow (test)    │
└──────────────────────────────────────────────────────┘
    ↓                         ↓
Ingestion Pipeline       LangGraph Engine
    ↓                         ↓
SQLite (rag.db)          Qdrant (local disk)
APScheduler (5s poll)
```

---

## 2. Two LangGraph Engines

### 2a. RAG Chat Graph (`graph_runner.py`) — Production Chat
Used by `/agent/chat` and `/agent/chat/stream`. A 3-node LangGraph StateGraph per request:

```
START → retrieve_node → generate_node → logger_node → END
```

| Node | Action |
|------|--------|
| `retrieve_node` | Embeds query via FastEmbed/OpenAI, searches Qdrant top-5, respects token budget |
| `generate_node` | Builds prompt (system + history + context), calls LLM OpenAI-compatible client |
| `logger_node` | Observability: logs tokens/cache/answer length, no state mutation |

The `stream_agent_graph` variant bypasses the graph and directly streams LLM tokens via OpenAI's streaming API, yielding SSE events (`context`, `chunk`, `done`).

### 2b. Master Orchestrator Graph (`master_graph.py`) — Dynamic Multi-Agent Workflow
Used by `/agent/test_master_workflow`. A dynamic router-based StateGraph:

```
START → router ──conditional──► document_subgraph ─┐
                              ► retrieval_subgraph  ├─► back to router ─► ... ─► END
                              ► analysis_subgraph   │
                              ► report_subgraph     ┘
```

The `router_node` reads `workflow_agents[current_step_index]` from `AgentState` and dispatches to the matching subgraph. Each subgraph increments `current_step_index` on completion. The pipeline is fully configurable at request time.

**Subgraph Pipeline Summary:**

| Subgraph | Nodes | Key Output |
|----------|-------|------------|
| `document_subgraph` | file_type_routing → parse_pdf/csv/png → chunk → insert | `document_chunks`, vectors upserted to Qdrant |
| `retrieval_subgraph` | build_query → vector_search → rerank_results (>30% threshold) | `retrieved_docs` |
| `analysis_subgraph` | construct_prompt → run_llm → generate_analysis | `analysis_result` (markdown) |
| `report_subgraph` | structure_report (HTML) → generate_pdf (xhtml2pdf to `reports/`) | `final_report` (PDF path on disk) |

---

## 3. Ingestion Pipeline

The ingestion process is fully asynchronous and config-driven (no manual steps):

```
POST /admin/ingest
    ↓
Save file to data/uploads/
Create SQLite job (PROCESSING)
    ↓
BackgroundTask: execute_parsing_stage
    ├── local_markdown: PyPDF2 (PDF) or aiofiles (text)
    └── cloud_llamaparse: LlamaParse API → Markdown (or local OCR fallback)
    ↓
chunk_markdown_content: header-split (#-####) + sentence window
    800-char chunks, 100-char overlap, metadata: {file_name, page_label, heading}
    ↓
Chunks stored in SQLite (job → EMBEDDING_AND_INDEXING)
    ↓
APScheduler (every 5s): poll_ingestion_queue
    ├── local_fastembed: BAAI/bge-small-en-v1.5 (384-dim)
    └── cloud_openai: OpenAI Embeddings API (1536-dim)
    ↓
Upsert PointStructs to Qdrant "rag_text"
    ↓
Job → COMPLETE
```

---

## 4. Storage Architecture

### SQLite (`data/rag.db`)
| Table | Purpose |
|-------|---------|
| `ingestion_jobs` | Multi-stage job state machine (status + chunks JSON in document_id) |
| `agent_definitions` | Agent registry: system base agents + user-configured clones |
| `agent_sessions` | Session tracking + rolling summary digest |
| `session_context_cache` | Query dedup cache (prevents re-embedding identical queries) |
| `conversation_messages` | Full conversation audit trail per session |

### Qdrant Vector Store (`data/qdrant/`)
| Collection | Dimensions | Purpose |
|------------|-----------|---------|
| `rag_text` | 384 or 1536 | Text chunk embeddings (auto-selects size based on embedding_api_key) |
| `rag_image` | 512 | Image embeddings (Phase 2 multimodal) |

Mode: embedded local disk storage (file-locked singleton). Remote Qdrant supported via `IMMERSIVE_RAG_QDRANT_URL`.

---

## 5. Agent Registry

System stores two base (immutable) agents seeded on startup:
- **`doc_analyzer`** — strict document-only analyst; tools: `export_pdf`, `export_csv`
- **`general_assistant`** — helpful corporate assistant; tools: `export_pdf`

Users can clone any base agent to create custom agents with overridden system prompts, `enabled_tools`, and `model_settings` (temperature, max_tokens). Custom agents are stored in `agent_definitions` and surfaced via `GET /agent/registry`.

LLM credentials can be updated at runtime via `POST /admin/llm-config` (no server restart required). The LLM client is a resettable singleton in `llm_client.py`.

---

## 6. Memory & Context Management (3-Tier)

| Tier | Mechanism | Storage | Behavior |
|------|-----------|---------|---------|
| 1 — Cache | `session_context_cache` | SQLite | Deduplicates identical queries by hash within a session |
| 2 — Recent History | `conversation_messages` | SQLite | Last 4 turns passed verbatim in every LLM prompt |
| 3 — Summary Digest | `agent_sessions.summary_digest` | SQLite | LLM compresses older turns to ≤256 tokens; refreshed every 4 turns (after 8 messages) |

---

## 7. Tool Services

| Tool | Endpoint | Implementation |
|------|----------|---------------|
| CSV Export | `POST /agent/tools/export/csv` | Parses markdown tables → CSV string |
| PDF Export | `POST /agent/tools/export/pdf` | Markdown → HTML → xhtml2pdf → PDF bytes |

---

## 8. Configuration (`AppConfig`)

All settings are environment-variable driven via `.env` in the backend root. Key settings:

```env
IMMERSIVE_RAG_LLM_API_KEY=           # Required for chat generation
IMMERSIVE_RAG_LLM_BASE_URL=          # Corporate proxy override
IMMERSIVE_RAG_LLM_MODEL=gpt-4o       # Default
IMMERSIVE_RAG_OPENAI_API_KEY=        # Embedding API (unset → FastEmbed fallback)
IMMERSIVE_RAG_EMBEDDING_MODEL=text-embedding-3-small
IMMERSIVE_RAG_LLAMA_PARSE_API_KEY=   # Cloud PDF parsing (unset → local OCR)
IMMERSIVE_RAG_BYPASS_SSL_VERIFY=true # For corporate SSL proxies
IMMERSIVE_RAG_QDRANT_URL=            # Remote Qdrant (unset → local disk)
```

---

## 9. Phase 1 Status vs. Plan

| `my_plan.md` Feature | Status |
|----------------------|--------|
| Document upload | ✅ Implemented (`/admin/ingest`, `/admin/ingest/bulk`) |
| Base agent configuration | ✅ Implemented (agent registry + `/agent/configure`) |
| Static multi-agent workflows | ✅ Implemented (Master Orchestrator + 4 subgraphs) |
| Asynchronous execution | ✅ Implemented (BackgroundTasks + APScheduler) |
| Job tracking | ✅ Implemented (SQLite state machine) |
| Tool execution service | ✅ Implemented (export_tools: CSV + PDF) |
| Structured output (PDF reports) | ✅ Implemented (report_agent subgraph) |
| Parallel execution | ❌ Phase 2 |
| Observability dashboards | ❌ Phase 2 |
| Dynamic workflow planning | ❌ Phase 2 |
