"""
Master Router Graph — Planner-Executor pattern.

The orchestrator first creates a multi-step PLAN from the user query, then
EXECUTES each step sequentially, chaining outputs as context.

Step action types:
  - "sub_agent"   → Call a configured sub-agent's RAG pipeline
  - "export_csv"  → Extract tables from the accumulated answer and download as CSV
  - "export_pdf"  → Generate a formatted PDF from accumulated answer content

SSE event types emitted (superset of standard graph_runner events):
  data: {"type": "plan",       "steps": [...]}
  data: {"type": "step_start", "step": int, "label": str, "action": str}
  data: {"type": "step_done",  "step": int}
  data: {"type": "routing",    "agent": str, "intent": str}
  data: {"type": "context",    "chunks": [...], "cache_hit": bool, "tokens_used": int}
  data: {"type": "chunk",      "text": str}
  data: {"type": "pdf_ready",  "data": str (base64), "filename": str}
  data: {"type": "csv_ready",  "data": str (base64), "filename": str}
  data: {"type": "clarification", "question": str, "options": [...]}
  data: {"type": "done"}
"""
import json
import logging
from typing import Generator

from app.engine.agents.conversation_memory import ConversationMemory
from app.engine.agents.llm_client import get_llm_client
from app.core.config import config

logger = logging.getLogger(__name__)


# ── Step Schema ─────────────────────────────────────────────────────────
# Each step returned by the planner:
# {
#   "step": <int>,
#   "action_type": "sub_agent" | "export_csv" | "export_pdf",
#   "agent": "<sub-agent name or null>",
#   "instruction": "<what this step should do>",
#   "label": "<human-readable step description>"
# }

# ── Planner ─────────────────────────────────────────────────────────────
def _plan_steps(question: str, sub_agent_names: list[str]) -> list[dict]:
    """
    Asks the LLM to decompose the user query into an ordered list of steps.
    Returns a list of step dicts.
    """
    client = get_llm_client()
    agent_list_str = "\n".join(f"- {a}" for a in sub_agent_names) if sub_agent_names else "- (none configured)"

    plan_prompt = f"""You are a planning AI for a multi-agent orchestration system.
Decompose the user query into a sequential list of steps that fully satisfies the request.

Available sub-agents (for knowledge retrieval, analysis, Q&A):
{agent_list_str}

Available tools (use EXACTLY these names for action_type):
- export_csv: Exports tabular/structured data from previous step as a CSV download. Use ONLY when user explicitly asks for CSV/spreadsheet export.
- export_template: Opens the branded Document Template generator with the generated content pre-filled. Use when user asks for ANY formal document: FRD, BRD, proposal, specification, report, executive summary, contract, pitch document, or any named document type. This uses full professional styling with brand colours.
- export_pdf: Generates a quick plain PDF download. Use ONLY when user asks for a simple PDF/download and has NOT requested a specific document type.

RULES:
1. Always start with a "sub_agent" step to retrieve/generate content before any export.
2. Only include export steps if the user explicitly asks for an export/document/download.
3. CSV of a table → export_csv AFTER sub_agent step.
4. Formal document (FRD, BRD, report, proposal, executive summary, spec) → ALWAYS use export_template, NOT export_pdf.
5. Generic "save as PDF" / "download as PDF" with no document type → export_pdf.
6. Multiple sub_agent steps are allowed (e.g., retrieve analysis, then write summary).
7. Assign the most relevant sub-agent. If only one agent, use it for all sub_agent steps.
8. Keep steps minimal — don't add steps the user didn't ask for.

Respond ONLY with a valid JSON object (no markdown, no explanation):
{{
  "needs_clarification": false,
  "clarification_question": null,
  "clarification_options": [],
  "steps": [
    {{
      "step": 1,
      "action_type": "sub_agent",
      "agent": "<agent name>",
      "instruction": "<exact task for this step — be specific>",
      "label": "<human label, e.g. 'Drafting FRD content'>"
    }}
  ]
}}

User query: {question}"""

    try:
        response = client.chat.completions.create(
            model=config.llm_model,
            messages=[{"role": "user", "content": plan_prompt}],
            max_tokens=512,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()

        # Step 1: robustly extract the outermost JSON object.
        # This completely ignores leading/trailing text and markdown backticks,
        # preventing truncation bugs if the JSON contains internal backticks.
        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end != -1 and end > start:
            raw = raw[start:end + 1]

        # Step 2: sanitize literal control chars inside JSON string values.
        # Corporate models often emit actual \n/\t/\r inside string fields.
        import re
        raw = re.sub(r'[\r\n\t]', ' ', raw)
        raw = re.sub(r'  +', ' ', raw).strip()

        # Layer 4: replace Python literals that are invalid JSON
        # Corporate/older LLMs often output None, True, False instead of null, true, false
        raw = re.sub(r'\bNone\b', 'null', raw)
        raw = re.sub(r'\bTrue\b', 'true', raw)
        raw = re.sub(r'\bFalse\b', 'false', raw)

        # Layer 5: try json.loads, fall back to ast.literal_eval for single-quoted dicts
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            import ast
            result = ast.literal_eval(raw)

        # Safety: fill in missing agents
        for step in result.get("steps", []):
            if step.get("action_type") == "sub_agent" and not step.get("agent") and sub_agent_names:
                step["agent"] = sub_agent_names[0]

        return result
    except Exception as e:
        logger.warning(f"Planner failed: {e}. Raw snippet: {locals().get('raw','')[:300]!r}. Using fallback.")
        return {
            "needs_clarification": False,
            "steps": [{
                "step": 1,
                "action_type": "sub_agent",
                "agent": sub_agent_names[0] if sub_agent_names else None,
                "instruction": question,
                "label": "Retrieving answer",
            }]
        }


# ── Main streaming function ─────────────────────────────────────────────
def stream_master_router_graph(
    question: str,
    agent_id: str,
    session_id: str,
    sub_agents: list[dict],
    model_settings: dict = None,
) -> Generator[str, None, None]:
    """
    Planner-Executor master orchestrator.
    1. Creates an ordered plan using the LLM
    2. Executes each step sequentially, streaming results to the user
    3. Chains step outputs as context for subsequent steps
    """
    memory = ConversationMemory(session_id, agent_id)

    # Build sub-agent name → definition map
    sub_agent_map = {a["name"]: a for a in sub_agents}
    sub_agent_names = list(sub_agent_map.keys())

    # ── Step 1: Plan ─────────────────────────────────────────────────
    plan_result = _plan_steps(question, sub_agent_names)

    # Handle clarification
    if plan_result.get("needs_clarification"):
        yield f"data: {json.dumps({'type': 'clarification', 'question': plan_result.get('clarification_question', ''), 'options': plan_result.get('clarification_options', [])})}\n\n"
        memory.append_turn("user", question)
        memory.append_turn("assistant", f"[Clarification requested] {plan_result.get('clarification_question', '')}")
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    steps = plan_result.get("steps", [])
    if not steps:
        steps = [{"step": 1, "action_type": "sub_agent", "agent": sub_agent_names[0] if sub_agent_names else None, "instruction": question, "label": "Answering your query"}]

    # Emit the plan to frontend
    yield f"data: {json.dumps({'type': 'plan', 'steps': steps})}\n\n"

    # ── Step 2: Execute each step ─────────────────────────────────────
    from app.engine.agents.graph_runner import stream_agent_graph

    accumulated_answer = ""   # full text built up across all steps
    last_step_answer = ""     # just the latest sub_agent answer (for CSV/PDF)

    for step in steps:
        step_num = step.get("step", 0)
        action = step.get("action_type", "sub_agent")
        label = step.get("label", f"Step {step_num}")

        # Announce step start
        yield f"data: {json.dumps({'type': 'step_start', 'step': step_num, 'label': label, 'action': action})}\n\n"

        # ── Sub-agent step ────────────────────────────────────────────
        if action == "sub_agent":
            agent_name = step.get("agent")
            instruction = step.get("instruction", question)

            # Build context-enriched instruction if we have prior results
            if accumulated_answer:
                instruction = (
                    f"{instruction}\n\n"
                    f"[Context from previous steps]\n{accumulated_answer[-3000:]}"
                )

            if agent_name and agent_name in sub_agent_map:
                target = sub_agent_map[agent_name]
                target_id = target["agent_id"]
                target_prompt = target.get("system_prompt", "")
                target_settings = {**target.get("model_settings", {}), **(model_settings or {})}
            else:
                # Fallback to first available or master agent's own pipeline
                if sub_agent_names:
                    target = sub_agent_map[sub_agent_names[0]]
                    target_id = target["agent_id"]
                    target_prompt = target.get("system_prompt", "")
                    target_settings = {**target.get("model_settings", {}), **(model_settings or {})}
                else:
                    target_id = agent_id
                    target_prompt = "You are a helpful assistant. Answer based on available context."
                    target_settings = model_settings or {}

            # Emit routing banner
            yield f"data: {json.dumps({'type': 'routing', 'intent': 'sub_agent', 'agent': agent_name or 'Master Orchestrator'})}\n\n"

            # Stream the sub-agent and collect answer
            step_answer = ""
            for sse in stream_agent_graph(
                question=instruction,
                agent_id=target_id,
                session_id=session_id,
                system_prompt=target_prompt,
                model_settings=target_settings,
            ):
                yield sse
                if sse.startswith("data: "):
                    try:
                        ev = json.loads(sse[6:])
                        if ev.get("type") == "chunk" and ev.get("text"):
                            step_answer += ev["text"]
                    except Exception:
                        pass

            last_step_answer = step_answer
            accumulated_answer += f"\n\n{step_answer}"

        # ── CSV export step ───────────────────────────────────────────
        elif action == "export_csv":
            source = last_step_answer or accumulated_answer
            if not source.strip():
                err = "\n\n> ⚠️ No content available to export as CSV."
                yield f"data: {json.dumps({'type': 'chunk', 'text': err})}\n\n"
            else:
                try:
                    import base64
                    from app.engine.tools.export_tools import extract_tables_to_csv
                    csv_data = extract_tables_to_csv(source)
                    csv_b64 = base64.b64encode(csv_data.encode("utf-8")).decode("utf-8")
                    yield f"data: {json.dumps({'type': 'csv_ready', 'data': csv_b64, 'filename': 'export.csv'})}\n\n"
                    logger.info(f"Master Router: step {step_num} — CSV exported")
                except Exception as e:
                    logger.error(f"CSV export failed: {e}")
                    err = "\n\n> ⚠️ CSV export failed. Please try using the toolbar button."
                    yield f"data: {json.dumps({'type': 'chunk', 'text': err})}\n\n"

        # ── PDF export step ───────────────────────────────────────────
        elif action == "export_pdf":
            source = accumulated_answer or last_step_answer
            if not source.strip():
                err = "\n\n> ⚠️ No content available to export as PDF."
                yield f"data: {json.dumps({'type': 'chunk', 'text': err})}\n\n"
            else:
                try:
                    import base64
                    from app.engine.tools.export_tools import generate_template_pdf

                    # Professional executive summary template skeleton
                    exec_template = """# Executive Summary

## Overview

## Key Findings

## Detailed Analysis

## Recommendations

## Appendix
"""
                    # Brand style — ImmersiveRAG palette
                    style = {
                        "primary_color":   "#EB8C00",
                        "secondary_color": "#E0301E",
                        "font_family":     "Helvetica, Arial, sans-serif",
                    }

                    pdf_bytes = generate_template_pdf(
                        template_markdown=exec_template,
                        filled_content=source,
                        style_config=style,
                    )
                    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
                    yield f"data: {json.dumps({'type': 'pdf_ready', 'data': pdf_b64, 'filename': 'executive_summary.pdf'})}\n\n"
                    logger.info(f"Master Router: step {step_num} — branded executive summary PDF exported")
                except Exception as e:
                    logger.error(f"PDF export failed: {e}")
                    err = "\n\n> ⚠️ PDF generation failed. Use the toolbar export button."
                    yield f"data: {json.dumps({'type': 'chunk', 'text': err})}\n\n"

        # ── Template (formal document) export step ───────────────────
        elif action == "export_template":
            source = accumulated_answer or last_step_answer
            if not source.strip():
                err = "\n\n> ⚠️ No content available for the document template."
                yield f"data: {json.dumps({'type': 'chunk', 'text': err})}\n\n"
            else:
                # Emit event to open the TemplateModal in the frontend with content pre-filled
                yield f"data: {json.dumps({'type': 'open_template_tool', 'content': source})}\n\n"
                logger.info(f"Master Router: step {step_num} — template tool opened with {len(source)} chars")

        # ── Step done ─────────────────────────────────────────────────
        yield f"data: {json.dumps({'type': 'step_done', 'step': step_num})}\n\n"

    # ── All steps complete ────────────────────────────────────────────
    memory.append_turn("user", question)
    memory.append_turn("assistant", accumulated_answer.strip())
    try:
        memory.maybe_refresh_summary()
    except Exception:
        pass
    yield f"data: {json.dumps({'type': 'done'})}\n\n"
