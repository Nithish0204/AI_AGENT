"""
PLANNER Node: Deciding What Tools to Use
==========================================

The planner examines the triage results and decides:
1. Which tools/data sources are needed
2. Whether this is a simple case (fast path) or complex (full path)

KEY CONCEPT - Planning Before Acting:
Instead of letting the LLM call tools ad-hoc (which wastes time and tokens),
we plan upfront. This is like a doctor deciding which tests to order
BEFORE running them, rather than ordering one test at a time.

Fast path: simple queries → skip critic/verification → faster + cheaper
Full path: complex issues → all tools + critic → slower but safer
"""

import time
from datetime import datetime, timezone

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from app.agent.state import CaseState
from app.agent.prompts import PLANNER_PROMPT
from app.models.schemas import PlannerResult
from app.config import get_settings


async def planner_node(state: CaseState) -> dict:
    """
    Decide which tools to call and whether to take the fast or full path.
    
    KEY CONCEPT - Cost/Latency Optimization:
    Not every case needs every tool. A simple "where's my order?" only
    needs get_order + search_knowledge_base. But a complex "refund for
    damaged high-value item" needs everything including fraud checks.
    Planning saves time and money.
    """
    start_time = time.time()
    settings = get_settings()
    
    llm = ChatGoogleGenerativeAI(
        model=settings.fast_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.0,
    )
    
    structured_llm = llm.with_structured_output(PlannerResult)
    
    prompt = PLANNER_PROMPT.format(
        intents=state.get("intents", []),
        order_id=state.get("order_id", ""),
        sentiment=state.get("sentiment", "neutral"),
        urgency=state.get("urgency", "medium"),
        summary=state.get("triage_summary", ""),
    )
    
    try:
        result: PlannerResult = await structured_llm.ainvoke([HumanMessage(content=prompt)])
        
        # Always include knowledge base search for any real issue
        tools = result.tools_needed
        if "search_knowledge_base" not in tools and state.get("intents"):
            tools.insert(0, "search_knowledge_base")
        
        # If we have an order ID, always look it up
        if state.get("order_id") and "get_order" not in tools:
            tools.append("get_order")
        
        duration = (time.time() - start_time) * 1000
        
        trace_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node": "planner",
            "event_type": "node_complete",
            "data": {
                "tools_needed": tools,
                "fast_path": result.fast_path,
                "reasoning": result.reasoning,
            },
            "duration_ms": round(duration, 2),
        }
        
        return {
            "execution_plan": tools,
            "fast_path": result.fast_path,
            "current_node": "planner",
            "trace_events": [trace_event],
        }
    
    except Exception as e:
        # Fallback: use all tools (safe default)
        duration = (time.time() - start_time) * 1000
        default_tools = ["search_knowledge_base"]
        if state.get("order_id"):
            default_tools.extend(["get_order", "get_customer_history"])
        
        return {
            "execution_plan": default_tools,
            "fast_path": False,
            "current_node": "planner",
            "trace_events": [{
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node": "planner",
                "event_type": "error",
                "data": {"error": str(e), "fallback_tools": default_tools},
                "duration_ms": round(duration, 2),
            }],
        }
