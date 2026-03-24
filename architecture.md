# ImmersiveRAG — Architecture & System Design

This document details the internal workings of the ImmersiveRAG platform, focusing on the synergy between the ingestion pipeline, the vector store, and the agentic reasoning engine.

---

## 1. System Overview

ImmersiveRAG is a decoupled architecture consisting of a **FastAPI** backend and a **Next.js** frontend. It is designed to be "local-first," meaning it can run entirely on a workstation without cloud dependencies (using FastEmbed and local LLMs), while also supporting high-scale corporate APIs (OpenAI/Groq/LlamaParse).

---

## 2. The Agentic Reasoning Engine (LangGraph)

The core of the chat system is a **LangGraph** workflow. Unlike simple RAG chains, LangGraph treats the process as a state machine, allowing for future expansion into multi-turn loops and tool-calling.

### Current 2-Node Workflow:
1.  **`retrieve_node`**:
    - Generates a dense vector for the user query.
    - Queries **Qdrant** for the top-5 most relevant text chunks.
    - Performs an optional token-budget check to ensure context stays within LLM limits.
2.  **`generate_node`**:
    - Assembles the "Final Prompt" using:
        - The Agent's **System Prompt**.
        - The retrieved **Context Chunks**.
        - **Conversation History** (Sliding Window or Summary).
    - Calls the LLM via an OpenAI-compatible client (Groq, Azure, or OpenAI).

---

## 3. Storage Architecture

The system uses two primary data stores:

### SQLite (`rag.db`)
- **Job Tracking**: Manages the multi-stage ingestion process.
- **Agent Registry**: Stores base agent definitions and user-configured clones.
- **Session Memory**: Tracks conversation history and provides a "sliding window" of recent context.
- **Summarization**: Stores "rolling digests" of long conversations to manage token pressure.

### Qdrant (Vector Store)
- **Embedded Vectors**: Stores the mathematical representations of document chunks.
- **Collection**: `rag_text` (default).
- **Dimensions**: Automatically adjusts based on the provider (384 for FastEmbed, 1536 for OpenAI).

---

## 4. Ingestion Pipeline Lifecycle

The ingestion process is asynchronous and VPN-aware:

1.  **Queue Stage**: File is saved to `data/uploads`, and a job is created in SQLite (`QUEUED`).
2.  **Parsing Stage**: 
    - `LlamaParse`: Converts complex PDFs into structured Markdown.
    - `Local Fallback`: Uses PyPDF2 for simple text extraction if LlamaParse is unavailable.
3.  **Chunking Stage**:
    - Splits Markdown by headers to preserve semantic context.
    - Uses a 10% overlap to ensure no information is lost at chunk boundaries.
4.  **Embedding & Indexing Stage**:
    - Batch-embeds chunks using the configured provider.
    - Upserts vectors and metadata into Qdrant.
5.  **Completion**: Job marked as `COMPLETE` and ready for retrieval.

---

## 5. Memory & Context Management

To keep the system fast and token-efficient, we use a **3-tier memory approach**:
- **Immediate Cache**: deduplicates exact queries within a session.
- **Recent History**: The last 10 messages are passed as full context.
- **Summarized Context**: Messages older than 10 turns are reduced to a concise summary (Summary Digest) to preserve long-term "narrative" without bloating the prompt.
