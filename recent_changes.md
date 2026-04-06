# Recent Changes & Improvements - Agentic Lab 🧪

## 🔐 1. Smart Configuration Status (Bug Fix)
- **Problem**: UI showed "OK" even if a connection test failed.
- **Fix**: Introduced a `verified` flag in `localStorage`. 
- **Header Logic**:
  - **Green (LLM/Embed OK)**: Successfully tested and saved.
  - **Amber (LLM/Embed SET)**: Key is present but untested or failed the last verification.
  - **Gray**: Not configured.
- **Input Reset**: Test status now clears automatically when you begin typing a new API key.

## 🎨 2. Brand Refresh & Header Redesign
- **Application Name**: Rebranded to **Agentic Lab**.
- **Layout**: Centered the title with a bold, 2xl font weight.
- **Aesthetics**: Removed the brand icon for a cleaner, more minimalist look while keeping the configuration pills accessible on the right.

## 🤖 3. Agent Configuration & Tunability
- **Advanced Layout**: Redesigned `AgentConfigModal` with a **two-column view** (Metadata on left, Prompt on right) to fit perfectly on standard screen resolutions without excessive vertical scrolling.
- **Enhanced LLM Parameters**:
  - **Max Output Tokens**: Increased support from 2,048 up to **10,000**.
  - **Max Context Tokens**: New slider (up to **10,000**) to control RAG retrieval budget.
  - **Top K (Context Chunks)**: New slider (1 to 20) to adjust the number of retrieved snippets.
- **Backend Sync**: Updated LangGraph orchestrator (`graph_runner.py`) to respect these new agent-specific overrides for both **Sync** and **Streaming** chat modes.

## 🧭 4. Sidebar UX Optimization
- **Dynamic Scrollability**: Fixed a UX bug where expanding settings pushed account links off-screen.
- **Sticky Actions**: Agent Selector, New Chat, and Chat History are now **static top-level elements**.
- **Static Footer**: Help Center and Account links are now pinned to the bottom.
- **Smooth Interaction**: Only the "Model Settings" and "Knowledge Base" sections are scrollable, featuring a thin, elegant custom scrollbar.

## 🛠️ 5. Backend Hardening & Configuration
- **Env Variable Support**: Core RAG parameters (`max_context_tokens`, `temperature`, `top_k`) are now fully configurable via `.env` without code changes.
- **Dynamic Config**: The `GET /admin/config/current` endpoint now pulls live values from the system configuration, ensuring the UI accurately reflects the backend state.

