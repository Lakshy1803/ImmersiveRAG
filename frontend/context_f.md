# ImmersiveRAG Frontend — Architecture Context

## Overview
The ImmersiveRAG frontend is a Next.js 14 (App Router) application serving as the visual control plane for the backend Shared Context Service. It lets developers upload documents, configure the ingestion pipeline, and interactively test RAG retrieval — all without touching Swagger or curl.

## Core Purpose
- Configure and trigger config-driven document ingestion (local or cloud extraction, local or company-API embeddings)
- Monitor ingestion job status with live polling
- Test the agent retrieval system via an interactive chat sandbox before wiring up external LangGraph agents
- No VPN steps or manual API confirmations required — everything is config-driven

## Directory Structure
```text
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx             # Inter font, dark theme, suppressHydrationWarning on html+body
│   │   ├── page.tsx               # Main dashboard: IngestionManager (left) + AgentChat (right) 50/50
│   │   └── globals.css            # Dark theme CSS variables, scrollbar styles
│   ├── components/
│   │   ├── Ingestion/
│   │   │   ├── IngestionManager.tsx  # Parent: owns config state, bridges ConfigPanel ↔ UploadZone
│   │   │   ├── ConfigPanel.tsx       # extraction_mode + embedding_mode toggle buttons
│   │   │   └── UploadZone.tsx        # Drag-and-drop upload, polls job status, displays progress
│   │   ├── Chat/
│   │   │   └── AgentChat.tsx         # Chat UI: sends question, renders ContextChunk cards with scores
│   │   └── ui/
│   │       └── Spinner.tsx           # Reusable animated loading spinner
│   └── lib/
│       └── api.ts                 # Typed fetch wrappers — all calls go via Next.js /api/* rewrite proxy
├── next.config.ts                 # Rewrites: /api/:path* → http://127.0.0.1:8000/:path*
├── package.json
└── tsconfig.json
```

## API Proxy Setup
All backend calls are made relative (`/api/...`) — no direct `127.0.0.1:8000` in component code. `next.config.ts` handles the proxy rewrite to the backend:
```ts
rewrites: [{ source: '/api/:path*', destination: 'http://127.0.0.1:8000/:path*' }]
```
This avoids CORS issues and makes the base URL configurable in one place.

## Type Contract (`src/lib/api.ts`)
```ts
// Request to backend
{ question: string, session_id: string, agent_id: string, top_k: number, max_tokens: number }

// Response from backend
{
  agent_id: string, session_id: string, question: string,
  extracted_context: Array<{ chunk_id: string, document_id: string, text: string, score: number, modality: string }>,
  total_tokens_used: number, cache_hit: boolean
}
```
> ⚠️ Backend uses `question` (not `query`) and `total_tokens_used` (not `total_tokens`). chunk ID field is `chunk_id` (not `id`).

## Data Lifecycle

### 1. Ingestion Flow
1. `ConfigPanel` → user selects `extraction_mode` (`local_markdown` | `cloud_llamaparse`) and `embedding_mode` (`local_fastembed` | `cloud_openai`)
2. `IngestionManager` holds config state and passes it to `UploadZone` as props
3. `UploadZone` → user drops a file → calls `ImmersiveRagAPI.ingest(file, config)` → `POST /api/admin/ingest` (multipart)
4. On success: stores `job_id`, starts polling `GET /api/admin/ingest/{job_id}/status` every 3 seconds
5. UI renders status: `processing` → `embedding_and_indexing` → **`complete ✅`** or `failed ❌`

### 2. RAG Chat Flow
1. User types query in `AgentChat` → `POST /api/agent/query` with `{ question, session_id, agent_id }`
2. `session_id` is generated once on mount via `useEffect` (not during SSR, to avoid hydration mismatch)
3. Response renders message + `ContextChunk` cards showing text snippets, similarity scores, and UUID
4. A ⚡ **Cache Hit** badge appears if the backend's SQLite sliding window intercepted the repeated query

## Hydration Notes
- `suppressHydrationWarning` is set on `<html>`, `<body>`, all `<button>` elements in ConfigPanel, and the `<input>` in AgentChat to suppress false positives from browser autofill extensions injecting `fdprocessedid`
- `sessionId` is initialized to `''` on server and populated in `useEffect(() => setSessionId(...), [])` on client

## Styling
- Tailwind CSS with a custom dark palette (`bg-slate-950`, `bg-slate-900`, `bg-slate-800`)
- Premium micro-animations: hover gradients, glow shadows (`shadow-[0_0_15px_rgba(...)]`), smooth transitions
- Google Inter font via `next/font/google`
