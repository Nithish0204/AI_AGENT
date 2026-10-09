"""
LOGGER Node: Persisting the Full Trace
========================================

The final node in the graph. It saves everything to the database:
- The resolution decision
- All trace events (for the trace panel)
- Token usage and cost
- Latency per node

This data powers the supervisor dashboard and analytics.
"""

import json
import time
from datetime import datetime, timezone

from sqlalchemy import select
from app.agent.state import CaseState
from app.models.database import Case, get_async_session_factory


async def logger_node(state: CaseState) -> dict:
    """
    Persist the completed case to the database.
    
    KEY CONCEPT - Observability:
    Every decision the agent makes is logged with:
    - WHAT was decided (resolution type, amount)
    - WHY (reasoning, citations)
    - HOW (which nodes ran, tool calls, latency)
    - WHO approved it (auto, human, escalated)
    
    This audit trail is critical for:
    1. Debugging issues
    2. Measuring performance
    3. Regulatory compliance
    4. Continuous improvement
    """
    start_time = time.time()
    
    case_id = state.get("case_id", "")
    
    try:
        factory = get_async_session_factory()
        async with factory() as session:
            # Find or create the case
            result = await session.execute(
                select(Case).where(Case.id == case_id)
            )
            case = result.scalar_one_or_none()
            
            if case:
                # Update existing case
                case.status = state.get("status", "processing")
                case.detected_language = state.get("detected_language", "en")
                case.intents = json.dumps(state.get("intents", []))
                case.order_id = state.get("order_id", "")
                case.sentiment = state.get("sentiment", "neutral")
                case.urgency = state.get("urgency", "medium")
                case.triage_summary = state.get("triage_summary", "")
                case.resolution_type = state.get("resolution_type", "")
                case.resolution_amount = state.get("resolution_amount", 0.0)
                case.resolution_reasoning = state.get("resolution_reasoning", "")
                case.resolution_confidence = state.get("resolution_confidence", 0.0)
                case.risk_level = state.get("risk_level", "low")
                case.autonomy_level = state.get("autonomy_level", "")
                case.response_text = state.get("response_text", "")
                case.human_decision = state.get("human_decision")
                case.human_notes = state.get("human_notes")
                case.total_tokens = state.get("total_tokens", 0)
                case.total_cost = state.get("total_cost", 0.0)
                case.trace_events = json.dumps(state.get("trace_events", []), default=str)
                case.updated_at = datetime.now(timezone.utc)
                
                # Calculate total response time from trace events
                trace_events = state.get("trace_events", [])
                total_ms = sum(e.get("duration_ms", 0) for e in trace_events if e.get("duration_ms"))
                case.response_time_ms = total_ms
            else:
                # Create new case
                case = Case(
                    id=case_id,
                    customer_id=state.get("customer_id", ""),
                    customer_message=state.get("customer_message", ""),
                    detected_language=state.get("detected_language", "en"),
                    status=state.get("status", "processing"),
                    intents=json.dumps(state.get("intents", [])),
                    order_id=state.get("order_id", ""),
                    sentiment=state.get("sentiment", "neutral"),
                    urgency=state.get("urgency", "medium"),
                    triage_summary=state.get("triage_summary", ""),
                    resolution_type=state.get("resolution_type", ""),
                    resolution_amount=state.get("resolution_amount", 0.0),
                    resolution_reasoning=state.get("resolution_reasoning", ""),
                    resolution_confidence=state.get("resolution_confidence", 0.0),
                    risk_level=state.get("risk_level", "low"),
                    autonomy_level=state.get("autonomy_level", ""),
                    response_text=state.get("response_text", ""),
                    trace_events=json.dumps(state.get("trace_events", []), default=str),
                )
                session.add(case)
            
            await session.commit()
    
    except Exception as e:
        # Logging should NEVER break the agent flow
        print(f"⚠️ Logger error (non-fatal): {e}")
    
    duration = (time.time() - start_time) * 1000
    
    trace_event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "logger",
        "event_type": "node_complete",
        "data": {
            "case_id": case_id,
            "final_status": state.get("status", "processing"),
            "autonomy_level": state.get("autonomy_level", ""),
        },
        "duration_ms": round(duration, 2),
    }
    
    return {
        "current_node": "logger",
        "trace_events": [trace_event],
    }
