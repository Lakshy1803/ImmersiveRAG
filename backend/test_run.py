import asyncio
import os
import sys

# Add backend to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.api.agent_router import TestWorkflowRequest, test_master_workflow

async def main():
    req = TestWorkflowRequest(
        user_query="test",
        workflow_agents=["document_agent", "retrieval_agent", "analysis_agent", "report_agent"],
        uploaded_docs=[{"filename": "test.png", "path": "mock.png", "type": "png"}]
    )
    print("Running orchestrator...")
    res = await test_master_workflow(req)
    print("==== ORCHESTRATOR COMPLETE ====")
    print(f"Current Step Index: {res.get('current_step_index')}")
    final_report = res.get("final_report", "")
    print(f"Final Report Value:\n{final_report[:200]}..." if len(final_report) > 200 else f"Final Report Value: {final_report}")

if __name__ == "__main__":
    asyncio.run(main())
