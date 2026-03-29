---
name: guided-change-assistant
description: |
  Use this skill whenever the user asks for a feature, fix, bug, or refactor in the ImmersiveRAG project.
  The agent plans the change, directs the user where/what to modify (user does the coding),
  and then leads a structured verification phase using Swagger UI and browser DevTools.
---

# Guided Change Assistant Skill

This skill governs how to handle any code-change request in the ImmersiveRAG project.
The agent **never writes the code itself** — it produces a precise plan, directs the user to the exact lines/files to change, and then verifies the result.

---

## Phase 1 — PLAN

### 1.1 Read all relevant context first
Before planning, always read:
- `backend/context_b.md` — backend architecture, API contracts, data lifecycle
- `frontend/context_f.md` — frontend components, API calls, data flow
- `architecture.md` — system-level design and component interactions

If the request touches files not covered by context docs, read those source files directly.

### 1.2 Produce a written plan (implementation_plan.md)
Write a structured plan using the standard `implementation_plan.md` artifact format at:
`<appDataDir>/brain/<conversation-id>/implementation_plan.md`

The plan must include:

**For each backend change:**
- File path (absolute)
- Exact function / class / route to modify or create
- What to add/change/remove — be specific enough that the user can implement without guessing
- Any new Pydantic models, SQLite columns, or Qdrant fields required
- State any new environment variables needed

**For each frontend change:**
- File path (absolute)
- Component/function to modify
- What props, state, API calls, or UI elements to add/change
- Any new types needed in `api.ts`

**Cross-cutting concerns:**
- Order of changes (e.g. backend model before frontend type)
- Any migration steps (new SQLite columns, Qdrant collections)

### 1.3 Request user review
Use `notify_user` with `BlockedOnUser: true` and `PathsToReview` pointing to `implementation_plan.md`.
Do NOT proceed to Phase 2 until the user explicitly approves.

---

## Phase 2 — DIRECT

After approval, present changes as a numbered checklist of **exact human instructions**.

### Format for each change
```
### Change N — [File basename] ([BACKEND|FRONTEND])
📁 File: <absolute/path/to/file.py or .tsx>
📍 Location: function `foo()` / class `Bar` / route `POST /agent/chat` / component `AgentChat`

What to do:
  [Precise instruction — e.g. "Add a new field `heading: str` to the `ContextChunk` Pydantic model"]

Code to add/change:
  [Minimal code snippet the user should write — only the changed lines, not entire file]

⚠️  Notes: [Any gotchas, ordering requirements, or side effects]
```

### Rules for directing
- Never say "make changes" vaguely — always point to the exact line range or function
- If a new file is needed, give the full path and minimal scaffold content
- Group backend changes first, frontend second
- Remind user to save each file and check the terminal for reload/hot-reload errors after each group

---

## Phase 3 — VERIFY

After the user confirms all changes are done, run a structured verification sequence:

### 3a — Backend Verification (Swagger UI)

Direct the user to open `http://127.0.0.1:8000/docs`.

For each changed or new endpoint, provide:

```
### Test: [METHOD] [/path]

1. Click the endpoint in Swagger UI → "Try it out"
2. Fill in these values:
   [exact field → exact test value]
3. Click "Execute"
4. Expected HTTP status: [200 / 201 / 422 / etc.]
5. Expected response body shape:
   {
     "field": "expected_value"
   }
6. If you see [error X], it means [cause] → check [specific file/line]
```

Verify in this order:
1. Health check (`GET /health/ready`) — ensure server started without errors
2. Any new or modified endpoints — in logical dependency order
3. Any affected existing endpoints — ensure backward compatibility

### 3b — Frontend Verification (Browser DevTools)

Direct the user to open `http://localhost:3000` and then open **DevTools** (`F12`).

For each changed frontend feature:

```
### Test: [Feature name]

1. Open tab: [Console | Network | Application]
2. Action to perform: [exact UI interaction]
3. What to look for:
   - Console: [no errors | specific log message]
   - Network: [request to /api/path | response body field]
   - UI: [what should appear/change visually]
4. If [issue]: it means [root cause] → check [file]
```

Standard checks to always run:
- **Console tab**: No red errors after page load
- **Network tab**: Filter by `Fetch/XHR` → chat request goes to `/api/agent/chat/stream` (NOT `127.0.0.1:8000`)
- **Network tab**: SSE stream has `Content-Type: text/event-stream`
- **Application tab → Local Storage**: `immersive_rag_llm_config` key exists and has `apiKey`, `baseUrl`, `model` if LLM was configured

### 3c — End-to-End Test

After individual tests pass, always direct the user through a full E2E flow:

1. Upload a test document via the right sidebar
2. Poll until status shows `complete ✅`
3. Type a question in the chat
4. Observe:
   - SSE stream starts within 2 seconds
   - Source chunks appear with file name + page number
   - Answer streams token by token
   - Export buttons appear after response if agent has tools enabled

---

## Important Project Conventions (Always Respect)

### Backend
- All API routes use the `/api/*` Next.js proxy — never hardcode `127.0.0.1:8000` in frontend
- Job lifecycle: `processing → embedding_and_indexing → complete` (never skip states)
- LLM client is a singleton — always call `get_llm_client()`, never instantiate `OpenAI()` directly
- Qdrant is file-locked — always use `get_qdrant_client()` singleton
- SQLite is accessed via `get_connection()` context manager — never hold connections open
- New SQLite columns must include a migration `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` try/except block in `init_db()`
- Embedding dimension is `384` (FastEmbed) or `1536` (OpenAI) — auto-selected by `ensure_collection()`
- All new routes go in `admin_router.py` (admin ops) or `agent_router.py` (agent/chat ops)

### Frontend
- TypeScript types for new API fields go in `src/lib/api.ts`
- All fetch calls use `/api/*` paths (proxied by Next.js) — never a full URL
- `sessionId` must be initialized in `useEffect` (not during SSR) to avoid hydration mismatch
- Use `suppressHydrationWarning` on interactive elements prone to autofill injection
- Theme uses CSS custom properties (`bg-surface`, `text-on-surface`, etc.) — never hardcode hex colors
- Material Symbols icons via `<span className="material-symbols-outlined">{icon_name}</span>`

---

## Quick Reference — Key Files

| What | File |
|------|------|
| Backend API routes (admin) | `backend/app/api/admin_router.py` |
| Backend API routes (agent/chat) | `backend/app/api/agent_router.py` |
| LangGraph RAG pipeline | `backend/app/engine/agents/graph_runner.py` |
| Master Orchestrator | `backend/app/engine/agents/master_graph.py` |
| Subgraph agents | `backend/app/engine/agents/subgraphs/` |
| Ingestion pipeline | `backend/app/engine/ingestion/pipeline.py` |
| Embedder | `backend/app/engine/ingestion/embedder.py` |
| SQLite schema + seeding | `backend/app/storage/relations_db.py` |
| Qdrant collections | `backend/app/storage/vector_db.py` |
| Config (env vars) | `backend/app/core/config.py` |
| Scheduler | `backend/app/core/scheduler.py` |
| Pydantic API models | `backend/app/models/api_models.py` |
| Domain models + JobStatus | `backend/app/models/domain_models.py` |
| All frontend API calls + types | `frontend/src/lib/api.ts` |
| Chat + streaming UI | `frontend/src/components/Chat/AgentChat.tsx` |
| Agent selector + registry | `frontend/src/components/Navigation/SidebarLeft.tsx` |
| Ingestion panel | `frontend/src/components/Navigation/SidebarRight.tsx` |
| Agent config modal | `frontend/src/components/Agents/AgentConfigModal.tsx` |
| LLM config modal | `frontend/src/components/Settings/LLMConfigModal.tsx` |
| Page layout | `frontend/src/app/page.tsx` |
