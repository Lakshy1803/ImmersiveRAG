---
description: Register a new LangGraph Agent identity in the system
---
# Create New Agent Routine
1. Go to `backend/app/api/agent_router.py` (or similar registration module) and define the capabilities of the agent.
2. Ensure you have the system prompt for this agent defined.
3. Update `frontend/src/lib/api.ts` `AgentDefinition` type if any new config schema is generated.
4. Restart the backend Uvicorn server to re-load endpoints.
