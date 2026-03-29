# ImmersiveRAG Frontend — Architecture Context

## Overview
The ImmersiveRAG frontend is a Next.js 14 (App Router) application serving as the visual control plane for the backend Shared Context Service. It lets users upload documents, configure agents, use an interactive RAG chat interface, and manage ingestion settings — all without touching Swagger or curl.

## Core Purpose
- Configure and trigger config-driven document ingestion (local or cloud extraction, local or company-API embeddings)
- Monitor ingestion job status with live polling
- Select and configure agents (base or custom) from the Agent Registry
- Interactive streaming chat with the agent via SSE (`/agent/chat/stream`)
- No VPN steps or manual API confirmations required — everything is config-driven

## Directory Structure
```text
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx             # Inter font, dark theme, suppressHydrationWarning on html+body
│   │   ├── page.tsx               # Main dashboard layout
│   │   └── globals.css            # Dark theme CSS variables, scrollbar styles
│   ├── components/
│   │   ├── Ingestion/
│   │   │   ├── IngestionManager.tsx  # Parent: owns config state, bridges ConfigPanel ↔ UploadZone
│   │   │   ├── ConfigPanel.tsx       # extraction_mode + embedding_mode toggle buttons
│   │   │   └── UploadZone.tsx        # Drag-and-drop upload, polls job status, displays progress
│   │   ├── Chat/
│   │   │   └── AgentChat.tsx         # Streaming SSE chat UI: renders context chunks + token-by-token answer
│   │   └── ui/
│   │       └── Spinner.tsx           # Reusable animated loading spinner
│   └── lib/
│       └── api.ts                 # Typed fetch wrappers — all calls go via Next.js /api/* rewrite proxy
├── next.config.ts                 # Rewrites: /api/:path* → http://127.0.0.1:8000/:path*
├── package.json
└── tsconfig.json
```

## API Proxy Setup
All backend calls are made relative (`/api/...`) — no direct `127.0.0.1:8000` in component code. `next.config.ts` handles the proxy rewrite:
```ts
rewrites: [{ source: '/api/:path*', destination: 'http://127.0.0.1:8000/:path*' }]
```

## Backend API Endpoints Used by Frontend

| Endpoint | Used By |
|----------|---------|
| `POST /api/admin/ingest` | UploadZone — file + config form-data |
| `POST /api/admin/ingest/bulk` | UploadZone — bulk file upload |
| `GET /api/admin/ingest/{job_id}/status` | UploadZone — job status polling |
| `GET /api/admin/config/current` | ConfigPanel — display current model settings |
| `GET /api/admin/llm-config` | Model settings display (masked key) |
| `POST /api/admin/llm-config` | Runtime LLM credential update |
| `POST /api/admin/llm-config/test` | Test LLM credentials before saving |
| `GET /api/agent/registry` | Agent selector — list available agents |
| `POST /api/agent/chat/stream` | AgentChat — SSE streaming chat |
| `POST /api/agent/configure` | Create / update custom agent |
| `DELETE /api/agent/configure/{id}` | Delete custom agent |
| `POST /api/agent/tools/export/csv` | Export table content as CSV |
| `POST /api/agent/tools/export/pdf` | Export answer as PDF |

## Primary Chat API Contract (SSE Streaming)

**Request** (`POST /api/agent/chat/stream`):
```ts
{ question: string, agent_id: string, session_id: string }
```

**SSE Event stream** (3 event types in order):
```
data: {"type": "context", "chunks": [...], "cache_hit": bool, "tokens_used": int}
data: {"type": "chunk", "text": "..."}   ← one per LLM token
data: {"type": "done"}
```

**ContextChunk shape**:
```ts
{ chunk_id: string, document_id: string, text: string, score: number, modality: string, metadata: {} }
```

## Legacy Retrieval-Only API (backward compat)
```ts
// POST /api/agent/query
Request:  { question, agent_id, session_id, top_k, max_tokens }
Response: { agent_id, session_id, question, extracted_context: ContextChunk[], total_tokens_used, cache_hit }
```
> ⚠️ Uses `question` (not `query`) and `total_tokens_used` (not `tokens_used`).

## Data Lifecycle

### 1. Ingestion Flow
1. `ConfigPanel` → user selects `extraction_mode` (`local_markdown` | `cloud_llamaparse`) and `embedding_mode` (`local_fastembed` | `cloud_openai`)
2. `IngestionManager` holds config state and passes it to `UploadZone` as props
3. `UploadZone` → user drops file → `POST /api/admin/ingest` (multipart/form-data)
4. On success: stores `job_id`, polls `GET /api/admin/ingest/{job_id}/status` every ~3 seconds
5. UI shows status: `processing` → `embedding_and_indexing` → **`complete ✅`** or `failed ❌`

### 2. Streaming Chat Flow
1. User selects an agent from registry and types query in `AgentChat`
2. `session_id` is generated once on mount via `useEffect` (not SSR — avoids hydration mismatch)
3. `POST /api/agent/chat/stream` → EventSource / ReadableStream SSE
4. Frontend first renders context chunk cards (sources), then streams LLM tokens into the answer panel in real-time
5. Memory persisted server-side: last 4 turns verbatim + rolling summary digest after every 4th turn

## Hydration Notes
- `suppressHydrationWarning` is set on `<html>`, `<body>`, all `<button>` elements in ConfigPanel, and the `<input>` in AgentChat to suppress false positives from browser autofill extensions
- `sessionId` is initialized to `''` on server and populated in `useEffect(() => setSessionId(...), [])` on client

## Styling
- Tailwind CSS with a custom dark palette (`bg-slate-950`, `bg-slate-900`, `bg-slate-800`)
- Premium micro-animations: hover gradients, glow shadows (`shadow-[0_0_15px_rgba(...)]`), smooth transitions
- Google Inter font via `next/font/google`

## What's NOT Implemented Yet (Frontend)
- Full agent builder / configuration UI (backend API exists at `/agent/configure`)
- Master Orchestrator workflow builder UI (backend endpoint: `/agent/test_master_workflow`)
- PDF/CSV export buttons integrated in chat (backend tools exist at `/agent/tools/export/*`)
- LLM config settings panel (backend API exists at `/admin/llm-config`)
