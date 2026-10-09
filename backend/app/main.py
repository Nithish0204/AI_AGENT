"""
FastAPI Main Application: The API Server
==========================================

This is the entry point of the backend. It provides:
1. POST /api/chat → Process a customer message (returns SSE stream)
2. GET  /api/cases → List all cases
3. GET  /api/cases/{id} → Get case details with trace
4. POST /api/cases/{id}/approve → Supervisor approval
5. GET  /api/dashboard/stats → Analytics for the dashboard
6. GET  /api/health → Health check

KEY CONCEPT - Server-Sent Events (SSE):
Instead of waiting for the full response (which takes 10-30 seconds),
we STREAM trace events to the frontend as each node completes.
The customer sees the agent "thinking" in real-time. This is the
key differentiator for the demo — the live trace panel.
"""

import json
import uuid
import asyncio
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.schemas import (
    ChatRequest, CaseResponse, ApprovalRequest, DashboardStats, TraceEvent,
)
from app.models.database import Case, Customer, init_db, get_db_session, get_async_session_factory
from app.agent.graph import get_agent_graph
from app.agent.state import CaseState
from app.seed.seed_data import seed_database
from app.knowledge.indexer import index_policies


# ============================================================
# Application Lifespan (startup/shutdown)
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run setup on startup, cleanup on shutdown."""
    print("🚀 Starting AI Customer Support Agent...")
    
    # Initialize database
    await init_db()
    print("✅ Database initialized")
    
    # Seed data (idempotent)
    try:
        seed_database()
        print("✅ Seed data loaded")
    except Exception as e:
        print(f"⚠️ Seed data warning: {e}")
    
    # Index policies (idempotent)
    try:
        settings = get_settings()
        if settings.gemini_api_key and settings.gemini_api_key != "your-gemini-api-key-here":
            index_policies()
            print("✅ Knowledge base indexed")
        else:
            print("⚠️ GEMINI_API_KEY not set — skipping knowledge base indexing")
    except Exception as e:
        print(f"⚠️ Indexing warning: {e}")
    
    print("🎯 Agent ready! API docs at http://localhost:8000/docs")
    yield
    print("👋 Shutting down...")


# ============================================================
# Create FastAPI App
# ============================================================

app = FastAPI(
    title="AI Customer Support Resolution Agent",
    description="An intelligent agent that resolves customer complaints with explainable, safe, and measurable decisions.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API documentation."""
    return RedirectResponse(url="/docs")


# ============================================================
# Chat Endpoint (SSE Streaming)
# ============================================================

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Process a customer message through the agent graph.
    Returns a Server-Sent Event stream with trace events and the final response.
    
    KEY CONCEPT - SSE Streaming:
    Instead of returning one big JSON after 30 seconds, we stream
    updates as they happen:
      event: trace → node started, tool called, etc.
      event: response → final customer response
      event: done → processing complete
    
    The frontend shows each update in the trace panel in real-time.
    """
    settings = get_settings()
    
    if not settings.gemini_api_key or settings.gemini_api_key == "your-gemini-api-key-here":
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
    
    # Generate case ID
    case_id = request.case_id or f"CASE-{uuid.uuid4().hex[:8].upper()}"
    
    # Look up customer tier
    customer_tier = "standard"
    try:
        factory = get_async_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(Customer).where(Customer.id == request.customer_id)
            )
            customer = result.scalar_one_or_none()
            if customer:
                customer_tier = customer.tier
    except Exception:
        pass
    
    # Initial state for the graph
    initial_state: CaseState = {
        "case_id": case_id,
        "customer_id": request.customer_id,
        "customer_message": request.message,
        "customer_tier": customer_tier,
        "conversation_history": [],
        "trace_events": [],
        "critic_retry_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "processing",
    }
    
    async def event_stream():
        """Generate SSE events as the graph processes each node."""
        graph = get_agent_graph()
        
        # Send initial event
        yield _sse_event("trace", {
            "node": "system",
            "event_type": "case_started",
            "data": {"case_id": case_id, "customer_id": request.customer_id},
        })
        
        try:
            # Run the graph and stream node outputs
            # LangGraph's astream gives us state updates after each node
            config = {"configurable": {"thread_id": case_id}}
            
            final_state = None
            async for event in graph.astream(initial_state, config=config):
                # event is a dict with node_name → state_update
                for node_name, state_update in event.items():
                    if node_name == "__end__":
                        continue
                    
                    final_state = state_update if final_state is None else {**final_state, **state_update}
                    
                    # Stream trace events from this node
                    trace_events = state_update.get("trace_events", [])
                    for te in trace_events:
                        yield _sse_event("trace", te)
                    
                    # If we have a response, stream it
                    if "response_text" in state_update and state_update["response_text"]:
                        yield _sse_event("response", {
                            "case_id": case_id,
                            "response_text": state_update["response_text"],
                            "resolution_type": state_update.get("resolution_type",
                                final_state.get("resolution_type", "") if final_state else ""),
                            "resolution_amount": state_update.get("resolution_amount",
                                final_state.get("resolution_amount", 0) if final_state else 0),
                            "autonomy_level": state_update.get("autonomy_level",
                                final_state.get("autonomy_level", "") if final_state else ""),
                            "confidence": state_update.get("resolution_confidence",
                                final_state.get("resolution_confidence", 0) if final_state else 0),
                            "status": state_update.get("status",
                                final_state.get("status", "processing") if final_state else "processing"),
                            "detected_language": state_update.get("detected_language",
                                final_state.get("detected_language", "en") if final_state else "en"),
                        })
            
            yield _sse_event("done", {"case_id": case_id})
            
        except Exception as e:
            yield _sse_event("error", {"message": str(e), "case_id": case_id})
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# Case Management Endpoints
# ============================================================

@app.get("/api/cases")
async def list_cases(
    status: str = None,
    limit: int = 50,
):
    """List all cases, optionally filtered by status."""
    factory = get_async_session_factory()
    async with factory() as session:
        query = select(Case).order_by(Case.created_at.desc()).limit(limit)
        if status:
            query = query.where(Case.status == status)
        
        result = await session.execute(query)
        cases = result.scalars().all()
        
        return [
            {
                "case_id": c.id,
                "customer_id": c.customer_id,
                "status": c.status,
                "customer_message": c.customer_message[:200],
                "resolution_type": c.resolution_type,
                "resolution_amount": c.resolution_amount,
                "autonomy_level": c.autonomy_level,
                "confidence": c.resolution_confidence,
                "sentiment": c.sentiment,
                "urgency": c.urgency,
                "detected_language": c.detected_language,
                "triage_summary": c.triage_summary,
                "response_time_ms": c.response_time_ms,
                "created_at": c.created_at.isoformat() if c.created_at else "",
            }
            for c in cases
        ]


@app.get("/api/cases/{case_id}")
async def get_case(case_id: str):
    """Get full case details including trace events."""
    factory = get_async_session_factory()
    async with factory() as session:
        result = await session.execute(select(Case).where(Case.id == case_id))
        case = result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        return {
            "case_id": case.id,
            "customer_id": case.customer_id,
            "status": case.status,
            "customer_message": case.customer_message,
            "detected_language": case.detected_language,
            "intents": json.loads(case.intents) if case.intents else [],
            "order_id": case.order_id,
            "sentiment": case.sentiment,
            "urgency": case.urgency,
            "triage_summary": case.triage_summary,
            "resolution_type": case.resolution_type,
            "resolution_amount": case.resolution_amount,
            "resolution_reasoning": case.resolution_reasoning,
            "resolution_confidence": case.resolution_confidence,
            "risk_level": case.risk_level,
            "autonomy_level": case.autonomy_level,
            "response_text": case.response_text,
            "human_decision": case.human_decision,
            "human_notes": case.human_notes,
            "total_tokens": case.total_tokens,
            "total_cost": case.total_cost,
            "response_time_ms": case.response_time_ms,
            "trace_events": json.loads(case.trace_events) if case.trace_events else [],
            "created_at": case.created_at.isoformat() if case.created_at else "",
            "updated_at": case.updated_at.isoformat() if case.updated_at else "",
        }


@app.post("/api/cases/{case_id}/approve")
async def approve_case(case_id: str, approval: ApprovalRequest):
    """
    Supervisor approves, edits, or rejects a case.
    
    KEY CONCEPT - Human-in-the-Loop Completion:
    When a case is in "awaiting_approval" state, the supervisor
    can approve it (proceed with the AI's recommendation),
    edit it (modify the resolution), or reject it (send back for re-review).
    """
    factory = get_async_session_factory()
    async with factory() as session:
        result = await session.execute(select(Case).where(Case.id == case_id))
        case = result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        if case.status != "awaiting_approval":
            raise HTTPException(status_code=400, detail=f"Case is not awaiting approval (status: {case.status})")
        
        case.human_decision = approval.decision
        case.human_notes = approval.notes
        
        if approval.decision == "approved":
            case.status = "resolved"
        elif approval.decision == "edited":
            case.status = "resolved"
            if approval.modified_resolution_type:
                case.resolution_type = approval.modified_resolution_type
            if approval.modified_amount is not None:
                case.resolution_amount = approval.modified_amount
            if approval.modified_response:
                case.response_text = approval.modified_response
        elif approval.decision == "rejected":
            case.status = "escalated"
        
        case.updated_at = datetime.now(timezone.utc)
        await session.commit()
        
        return {"status": "ok", "case_id": case_id, "new_status": case.status}


# ============================================================
# Dashboard Analytics
# ============================================================

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """Get aggregate statistics for the supervisor dashboard."""
    factory = get_async_session_factory()
    async with factory() as session:
        # Total cases
        total_result = await session.execute(select(func.count(Case.id)))
        total_cases = total_result.scalar() or 0
        
        # Cases by status
        auto_result = await session.execute(
            select(func.count(Case.id)).where(Case.autonomy_level == "auto_resolve")
        )
        auto_resolved = auto_result.scalar() or 0
        
        approval_result = await session.execute(
            select(func.count(Case.id)).where(Case.autonomy_level == "human_approval")
        )
        human_approved = approval_result.scalar() or 0
        
        escalated_result = await session.execute(
            select(func.count(Case.id)).where(Case.autonomy_level == "escalate")
        )
        escalated = escalated_result.scalar() or 0
        
        # Pending cases
        pending_result = await session.execute(
            select(func.count(Case.id)).where(Case.status == "awaiting_approval")
        )
        pending = pending_result.scalar() or 0
        
        # Average response time
        avg_time_result = await session.execute(
            select(func.avg(Case.response_time_ms)).where(Case.response_time_ms > 0)
        )
        avg_response_time = avg_time_result.scalar() or 0
        
        # Average cost
        avg_cost_result = await session.execute(
            select(func.avg(Case.total_cost)).where(Case.total_cost > 0)
        )
        avg_cost = avg_cost_result.scalar() or 0
        
        # Top intents
        all_cases_result = await session.execute(select(Case.intents).where(Case.intents.isnot(None)))
        intent_counts = {}
        for (intents_json,) in all_cases_result:
            try:
                intents = json.loads(intents_json) if intents_json else []
                for intent in intents:
                    intent_counts[intent] = intent_counts.get(intent, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass
        
        top_intents = sorted(
            [{"intent": k, "count": v} for k, v in intent_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:10]
        
        auto_rate = (auto_resolved / total_cases * 100) if total_cases > 0 else 0
        esc_rate = (escalated / total_cases * 100) if total_cases > 0 else 0
        
        return DashboardStats(
            total_cases=total_cases,
            auto_resolved=auto_resolved,
            human_approved=human_approved,
            escalated=escalated,
            blocked=pending,
            avg_response_time_ms=round(avg_response_time, 2),
            avg_cost_per_case=round(avg_cost, 4),
            auto_resolution_rate=round(auto_rate, 1),
            escalation_rate=round(esc_rate, 1),
            top_intents=top_intents,
            # Assume 15 minutes per manual resolution at $25/hr
            estimated_hours_saved=round(auto_resolved * 0.25, 1),
            estimated_cost_saved=round(auto_resolved * 0.25 * 25, 2),
        )


# ============================================================
# Health & Utility Endpoints
# ============================================================

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "healthy",
        "api_key_configured": bool(settings.gemini_api_key and settings.gemini_api_key != "your-gemini-api-key-here"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/customers")
async def list_customers():
    """List all customers (for the demo UI)."""
    factory = get_async_session_factory()
    async with factory() as session:
        result = await session.execute(select(Customer).order_by(Customer.id))
        customers = result.scalars().all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "tier": c.tier,
                "total_orders": c.total_orders,
            }
            for c in customers
        ]


# ============================================================
# SSE Helper
# ============================================================

def _sse_event(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event message."""
    json_data = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {json_data}\n\n"
