# ImmersiveRAG Backend — Architecture Context

## Overview
The ImmersiveRAG backend is a Python FastAPI "Shared Context Service" for LangGraph multi-agent systems. It handles document ingestion (local or cloud extraction), semantic embedding (local FastEmbed or company API), vector storage in Qdrant, and session-scoped sliding window memory for token-efficient retrieval.

## Core Design Constraints
- **Local-First:** All data (Qdrant vectors, SQLite state) lives on disk — no external cloud calls unless explicitly configured via API keys.
- **Config-Driven Ingestion:** No manual VPN steps. Users select `extraction_mode` and `embedding_mode` via the frontend UI or API at time of upload.
- **Absolute Paths Only:** `config.py` computes all paths via `Path(__file__).parent.parent.parent` to prevent CWD-relative path bugs when Uvicorn is launched from different directories.
- **Single Qdrant Process:** Local Qdrant (file-based) does not support concurrent clients — always use the singleton via `get_qdrant_client()`.

## Directory Structure
```text
backend/
├── app/
│   ├── api/
│   │   ├── admin_router.py        # /admin/ingest, /admin/ingest/{id}/status, /admin/debug/*
│   │   ├── agent_router.py        # /agent/query  (main RAG entrypoint for LangGraph)
│   │   └── dependencies.py        # FastAPI Depends() injectors (config, db)
│   ├── core/
│   │   ├── config.py              # AppConfig (BaseSettings) — all paths computed as absolute
│   │   └── scheduler.py           # APScheduler: poll_ingestion_queue (5s), prune_stale_sessions (5min)
│   ├── engine/
│   │   ├── ingestion/
│   │   │   ├── pipeline.py        # execute_parsing_stage: extraction → chunk → save to SQLite
│   │   │   ├── parser.py          # run_llamaparse_extraction (cloud_llamaparse mode)
│   │   │   ├── chunker.py         # chunk_markdown_content: header-split (Markdown) + sentence-window (plain text)
│   │   │   └── embedder.py        # get_corporate_embeddings: local FastEmbed (384-dim) or company API (1536-dim)
│   │   ├── retrieval/
│   │   │   └── orchestrator.py    # RetrievalOrchestrator: cache check → Qdrant query → token budget
│   │   └── memory/
│   │       └── session_cache.py   # SQLite sliding window cache (per session_id)
│   ├── models/
│   │   ├── api_models.py          # AgentQueryRequest, AgentContextResponse, ContextChunk, IngestStatusResponse
│   │   └── domain_models.py       # JobStatus enum, DocumentIngestRequest, IngestionJob
│   └── storage/
│       ├── vector_db.py           # get_qdrant_client(), ensure_collection(), COLLECTION_NAME
│       └── relations_db.py        # get_connection(), init_db(), get_db_session()
├── data/                          # Runtime data (gitignored)
│   ├── rag.db                     # SQLite: ingestion_jobs, agent_sessions, session_context_cache
│   ├── qdrant/                    # Local Qdrant vector store (on-disk)
│   └── uploads/                   # Uploaded files saved here before processing
├── pyproject.toml                 # Declared deps including aiofiles, PyPDF2, fastembed
└── .env                           # API keys (gitignored) — see setup.md

```

## Key Enum: JobStatus
```
queued → processing → embedding_and_indexing → complete
                                             ↘ failed
```
- `processing`: Pipeline extracted text and saved chunks to `document_id` column in SQLite
- `embedding_and_indexing`: APScheduler picked up the job and is generating/upserting vectors
- `complete`: Vectors upserted to Qdrant successfully

## Ingestion Data Lifecycle
1. `POST /admin/ingest` — saves file to `data/uploads/`, creates SQLite job (`PROCESSING`), fires `execute_parsing_stage` as FastAPI BackgroundTask.
2. `pipeline.execute_parsing_stage` — reads `extraction_mode`:
   - `local_markdown`: PyPDF2 (PDF) or aiofiles (text) → plain text extraction
   - `cloud_llamaparse`: LlamaParse API call → Markdown extraction
   - Result chunked by `chunker.py` (header-split or sentence-window, 800-char chunks, 100-char overlap)
   - Chunks JSON-stored in `document_id` column, job updated to `EMBEDDING_AND_INDEXING`
3. `scheduler.poll_ingestion_queue` — runs every 5s, picks `EMBEDDING_AND_INDEXING` jobs:
   - Reads `embedding_mode` from `request_data` JSON column
   - Calls `get_corporate_embeddings(chunks, embedding_mode)` → vectors
   - Upserts `PointStruct` list to Qdrant `rag_text` collection
   - Job marked `COMPLETE`

## Retrieval Data Lifecycle
1. `POST /agent/query` (`AgentQueryRequest`: `question`, `session_id`, `agent_id`, `top_k`, `max_tokens`)
2. `RetrievalOrchestrator.retrieve()`:
   - Checks `EphemeralSessionCache` for exact query hash → returns cached chunks (`cache_hit=true`)
   - On miss: generates query embedding, calls `qdrant.query_points`, tiktoken-budgets results
   - Caches result in SQLite session window
3. Returns `AgentContextResponse` with `extracted_context: List[ContextChunk]` and `total_tokens_used`

## API Contract Quick Reference
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/admin/ingest` | Upload file (multipart/form-data) |
| GET | `/admin/ingest/{job_id}/status` | Poll job status |
| POST | `/agent/query` | RAG query (JSON body) |
| GET | `/admin/debug/vectors?limit=N` | Inspect Qdrant (debug) |
| DELETE | `/admin/debug/purge-vectors` | Wipe all vectors + job history (debug) |
| GET | `/docs` | Swagger UI |

## Environment Variables (`.env`)
```env
IMMERSIVE_RAG_OPENAI_API_KEY=<company-embedding-api-key>
IMMERSIVE_RAG_OPENAI_BASE_URL=<company-embedding-base-url>
IMMERSIVE_RAG_EMBEDDING_MODEL=<company-model-name>          # e.g. text-embedding-3-small
IMMERSIVE_RAG_LLAMA_PARSE_API_KEY=<optional-llamaparse-key>
IMMERSIVE_RAG_BYPASS_SSL_VERIFY=true                        # Set to true for corporate proxies
```
If `IMMERSIVE_RAG_OPENAI_API_KEY` is unset → embedding falls back to local FastEmbed (384-dim).
If `IMMERSIVE_RAG_LLAMA_PARSE_API_KEY` is unset → cloud_llamaparse extraction will fail; use `local_markdown`.

## LangGraph Orchestration (`graph_runner.py`)
The system uses a 2-node sync graph:
1. `retrieve_node`: Uses `RetrievalOrchestrator` to fetch top-5 chunks from Qdrant.
2. `generate_node`: Builds a prompt with context + history and calls the LLM (Groq/OpenAI).
Flow: `START` → `retrieve` → `generate` → `END`.

## Memory Strategy
- **Tier 1 (Short):** `session_context_cache` (SQLite) - avoids re-embedding/re-searching duplicate queries.
- **Tier 2 (History):** `conversation_messages` (SQLite) - full turn tracking for the agent.
- **Tier 3 (Summary):** `agent_sessions.summary_digest` - a rolling summary updated every 4 turns to keep long conversations within LLM context limits.
