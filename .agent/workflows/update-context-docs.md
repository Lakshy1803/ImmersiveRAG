---
description: Read all backend files and update context docs (context_b.md, context_f.md, architecture.md)
---
# Update Context Files After Backend Changes

Run this workflow whenever backend code changes have been made and the context docs need to be refreshed.

1. Read `my_plan.md` to understand the intended architecture and phase goals.

2. Explore the full backend directory structure:
   - `backend/app/api/` — routers and endpoints
   - `backend/app/core/` — config, scheduler, warnings
   - `backend/app/engine/agents/` — graph_runner, master_graph, state, llm_client, conversation_memory, subgraphs/
   - `backend/app/engine/ingestion/` — pipeline, parser, chunker, embedder
   - `backend/app/engine/retrieval/` — orchestrator
   - `backend/app/engine/tools/` — export tools
   - `backend/app/engine/document_processing/` — OCR parser
   - `backend/app/models/` — api_models, domain_models
   - `backend/app/storage/` — vector_db, relations_db
   - `backend/app/main.py`

3. Read every file found above in full to understand the current implementation.

4. Read the existing context docs to understand what is outdated:
   - `backend/context_b.md`
   - `frontend/context_f.md`
   - `architecture.md`

5. Compare existing docs against actual code and identify gaps/stale information such as:
   - New API endpoints added (routers)
   - New LangGraph nodes or subgraphs
   - New SQLite tables or columns
   - New Qdrant collections
   - New Pydantic models
   - Changed job lifecycle states
   - Changed memory strategy

6. Rewrite `backend/context_b.md` to accurately reflect:
   - Updated directory structure
   - All API endpoints (both routers, all methods)
   - Both LangGraph pipelines (RAG chat graph + Master Orchestrator)
   - All subgraphs with their node pipelines and outputs
   - AgentState TypedDict fields
   - Agent registry (system agents + custom agent flow)
   - SQLite tables and Qdrant collections
   - Ingestion lifecycle (stages and status transitions)
   - Memory strategy (3-tier)
   - All Pydantic API models
   - All environment variables

7. Update `frontend/context_f.md` to reflect any backend API changes:
   - New or changed endpoints that the frontend calls
   - Updated request/response shapes
   - Note any new backend features not yet wired to frontend UI

8. Rewrite `architecture.md` to reflect the full system design:
   - System overview diagram (text)
   - Both LangGraph engines with flow diagrams
   - Ingestion pipeline lifecycle (numbered steps)
   - Storage architecture (SQLite tables + Qdrant collections)
   - Agent registry design
   - Memory strategy table
   - Tool services
   - Config/env variables
   - Phase 1 completion status vs. my_plan.md

> **Note:** Only update context docs — do not change any source code. The frontend code is NOT being changed in this workflow step; context_f.md only reflects what the backend exposes.
