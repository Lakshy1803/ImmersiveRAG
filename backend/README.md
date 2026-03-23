# ImmersiveRAG Backend

> **📢 IMPORTANT**: For full deployment and setup instructions, please refer to the central **[setup.md](file:///e:/Projects/ImmersiveRAG/setup.md)** in the root directory.

This directory contains the Python-first multimodal RAG backend, built with FastAPI, LangGraph, and Qdrant.

## 1. Prerequisites

Install:
- Python `3.11+`
- `pip`
- Windows PowerShell if you are following the commands below on Windows

Required for the default PDF ingestion path:
- A LlamaParse API key

## 2. Create The Virtual Environment

From the repo root:

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
pip install -e backend[dev]
```

## 3. Create Local Config

Copy the example config:

```powershell
Copy-Item backend\.env.example backend\.env
```

`backend/.env` is for local overrides and should stay uncommitted.

## 4. Default Local Setup

The default configuration uses:
- LlamaParse for PDFs and images
- local native parsing only as a failure safety net
- local Qdrant on disk
- FastEmbed locally
- extractive answer generation locally

With the default setup, you need a LlamaParse API key for ingestion.

Important default paths:
- uploads, images, SQLite, and Qdrant data live under `backend/data`
- text vectors go to the Qdrant collection `rag_text`
- image vectors go to the Qdrant collection `rag_image`

## 5. Key Environment Variables

### Parsing and OCR

- `IMMERSIVE_RAG_PARSER_PROVIDER=llamaparse`
- `IMMERSIVE_RAG_LLAMA_PARSE_API_KEY=...`
- `IMMERSIVE_RAG_LLAMA_PARSE_RESULT_TYPE=markdown`
- `IMMERSIVE_RAG_LLAMA_PARSE_LANGUAGE=en`
- `IMMERSIVE_RAG_LLAMA_PARSE_NUM_WORKERS=1`
- `IMMERSIVE_RAG_LLAMA_PARSE_FAST_MODE=false`
- `IMMERSIVE_RAG_LLAMA_PARSE_PREMIUM_MODE=false`
- `IMMERSIVE_RAG_LLAMA_PARSE_VERBOSE=false`
- `IMMERSIVE_RAG_LLAMA_PARSE_DO_OCR=true`
- `IMMERSIVE_RAG_LLAMA_PARSE_CONFIDENCE_THRESHOLD=0.65`

Parser behavior:
- `llamaparse` is the only configured parser provider
- PDFs and images are both sent through LlamaParse first
- if LlamaParse fails, the service falls back to a local native parser for recovery

### Embeddings

- `IMMERSIVE_RAG_EMBEDDING_PROVIDER=fastembed` or `openai`
- `IMMERSIVE_RAG_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5`
- `IMMERSIVE_RAG_OPENAI_API_KEY=...`
- `IMMERSIVE_RAG_OPENAI_BASE_URL=...`
- `IMMERSIVE_RAG_OPENAI_EMBEDDING_MODEL=text-embedding-3-small`

### Generation

- `IMMERSIVE_RAG_GENERATION_PROVIDER=extractive` or `openai`
- `IMMERSIVE_RAG_GENERATION_API_KEY=...`
- `IMMERSIVE_RAG_GENERATION_BASE_URL=...`
- `IMMERSIVE_RAG_GENERATION_MODEL=openai/gpt-oss-120b`
- `IMMERSIVE_RAG_GENERATION_TEMPERATURE=0.2`
- `IMMERSIVE_RAG_GENERATION_MAX_COMPLETION_TOKENS=1200`

### Storage

- `IMMERSIVE_RAG_DATA_DIR=E:/Projects/ImmersiveRAG/backend/data`
- `IMMERSIVE_RAG_QDRANT_PATH=E:/Projects/ImmersiveRAG/backend/data/qdrant`
- `IMMERSIVE_RAG_QDRANT_URL=...`
- `IMMERSIVE_RAG_QDRANT_API_KEY=...`

### Security / Networking

- `IMMERSIVE_RAG_BYPASS_SSL_VERIFY=false` (Set to `true` to bypass certificate verification behind corporate proxies)

## 6. Run The API

From the repo root:

```powershell
backend\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --app-dir backend
```

The API exposes:
- `POST /admin/ingest` : Upload and start background ingestion
- `GET /admin/ingest/{job_id}/status` : Poll for ingestion job state
- `POST /agent/chat` : (New) Full RAG + LLM agent chat via LangGraph
- `POST /agent/query` : (Legacy) Retrieval-only context search
- `GET /agent/registry` : List available agents
- `POST /agent/configure` : Create custom agent clones
- `DELETE /admin/debug/purge-vectors` : Wipe all data for reset

## 7. Test The Code

From the repo root:

```powershell
backend\.venv\Scripts\Activate.ps1
pytest backend\tests
```

The current suite covers:
- health and readiness
- ingestion
- job persistence
- retrieval
- generation deduplication
- parser OCR/chunking behavior

## 8. Try A Local End-To-End Flow

Start the API, then upload a PDF or PNG through `/ingest`, then query `/query`.

Example tool flow:
1. Upload a `PDF`, `PNG`, or `JPG`
2. Wait for the returned job to reach `complete`
3. Ask a question through `/query`
4. Inspect citations and evidence in the response

## 9. Switch Providers Later

### Use OpenAI-compatible embeddings

```powershell
$env:IMMERSIVE_RAG_EMBEDDING_PROVIDER="openai"
$env:IMMERSIVE_RAG_OPENAI_API_KEY="your-key"
$env:IMMERSIVE_RAG_OPENAI_BASE_URL="https://your-openai-compatible-endpoint"
$env:IMMERSIVE_RAG_OPENAI_EMBEDDING_MODEL="text-embedding-3-small"
```

### Use Groq for generation

```powershell
$env:IMMERSIVE_RAG_LLM_API_KEY="your-groq-key"
$env:IMMERSIVE_RAG_LLM_BASE_URL="https://api.groq.com/openai/v1"
$env:IMMERSIVE_RAG_LLM_MODEL="llama-3.3-70b-versatile"
```

### Use Vertex Gemini through the OpenAI client

Keep:
- `IMMERSIVE_RAG_GENERATION_PROVIDER=openai`

Change:
- `IMMERSIVE_RAG_GENERATION_BASE_URL` to your OpenAI-compatible Vertex endpoint
- `IMMERSIVE_RAG_GENERATION_MODEL` to the deployed Gemini model name

## 10. What The System Stores

Local development storage layout:
- `backend/data/uploads` for uploaded source files
- `backend/data/images` for extracted page or figure images
- `backend/data/rag.db` for jobs and parsed document metadata
- `backend/data/qdrant` for local Qdrant data

Parsed document metadata currently includes:
- text blocks
- image regions
- page count
- page-level OCR metrics
- chunk bbox and reading order

## 11. Current Design Notes

Current retrieval design:
- lexical retrieval from stored parsed text
- multimodal dense retrieval through LlamaIndex
- separate Qdrant collections for text and image evidence
- reranking and evidence deduplication before answer generation

Current parsing design:
- LlamaParse is used first for PDFs and images and provides page-level layout items, confidence, and markdown/text output
- local native parsing remains as the recovery path when the remote parser fails
- chunk metadata preserves region coordinates and reading order
- OCR metrics are computed per page

## 12. Maintenance Rule

If any of the following change, update this README in the same change:
- setup steps
- environment variables
- provider selection
- storage layout
- API entrypoints
- runtime commands
- testing commands
