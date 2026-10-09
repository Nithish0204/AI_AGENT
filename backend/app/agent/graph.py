"""
Agent Graph: The Complete LangGraph Definition
================================================

This is THE core file — it defines the agent as a directed graph where:
- Nodes = processing steps (intake, triage, tools, reasoning, etc.)
- Edges = transitions between steps (some conditional)
- State = the CaseState that flows through every node

KEY CONCEPT - Agent as a Graph (not a chain):
A "chain" is linear: A → B → C. But real-world agents need BRANCHING:
- If injection detected → skip to blocked response
- If missing info → ask customer, then wait
- If critic fails → retry reasoner (loop!)
- If human approval needed → pause graph (interrupt)

LangGraph gives us this power with conditional edges and interrupts.

ARCHITECTURE DIAGRAM:
                    ┌─── [BLOCKED] ←── injection detected
                    │
    [INTAKE] ──→ [TRIAGE] ──→ [PLANNER] ──→ [TOOLS] ──→ [REASONER]
                    │                                         │
                    └── missing info → [ASK CUSTOMER]         │
                                                              ▼
                                                          [CRITIC]
                                                         ╱        ╲
                                                  pass ╱           ╲ fail (retry < max)
                                                      ▼             ╲
                                              [GUARDRAIL GATE]      → back to [REASONER]
                                             ╱       │       ╲         fail (retry >= max)
                                           ╱         │         ╲       → [ESCALATE]
                                     auto ╱    approval│     escalate╲
                                        ╱             │               ╲
                                  [RESPONDER]    [HUMAN PAUSE]    [RESPONDER]
                                       │              │               │
                                       └──────→ [LOGGER] ←───────────┘
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agent.state import CaseState
from app.agent.nodes.intake import intake_node
from app.agent.nodes.triage import triage_node
from app.agent.nodes.planner import planner_node
from app.agent.nodes.tools import tools_node
from app.agent.nodes.reasoner import reasoner_node
from app.agent.nodes.critic import critic_node
from app.agent.nodes.guardrails import guardrail_gate_node
from app.agent.nodes.responder import responder_node
from app.agent.nodes.logger import logger_node
from app.config import get_settings


# ============================================================
# Conditional Edge Functions
# ============================================================

def route_after_intake(state: CaseState) -> str:
    """
    After intake: if injection detected, go straight to blocked response.
    Otherwise, continue to triage.
    
    KEY CONCEPT - Conditional Edges:
    Instead of a fixed A→B connection, we can route dynamically:
    return "blocked" → goes to responder (with rejection message)
    return "triage" → continues normal flow
    """
    if state.get("injection_detected", False) and state.get("injection_score", 0) > 0.6:
        return "blocked"
    return "triage"


def route_after_triage(state: CaseState) -> str:
    """
    After triage: if critical info is missing, ask the customer.
    Otherwise, continue to planner.
    """
    missing = state.get("missing_info", [])
    # Only block for truly critical missing info
    critical_missing = [m for m in missing if m in ("order_id",) and 
                       any(i in state.get("intents", []) for i in 
                           ("refund_request", "delivery_complaint", "order_status"))]
    
    if critical_missing and state.get("triage_confidence", 1.0) < 0.5:
        return "ask_info"
    return "planner"


def route_after_critic(state: CaseState) -> str:
    """
    After critic: if passed → guardrail gate.
    If failed and retries left → back to reasoner.
    If failed and no retries → escalate via guardrail gate.
    
    KEY CONCEPT - Retry Loop:
    The graph can loop! If the critic finds issues, we go BACK
    to the reasoner with the critic's feedback. The reasoner
    tries again, addressing the specific issues raised.
    But we limit retries (max 1) to prevent infinite loops.
    """
    settings = get_settings()
    
    if state.get("critic_passed", False):
        return "guardrail_gate"
    
    retry_count = state.get("critic_retry_count", 0)
    if retry_count <= settings.max_critic_retries:
        return "reasoner_retry"  # Go back to reasoner with feedback
    
    return "guardrail_gate"  # Max retries exceeded, let guardrail decide


def route_after_fast_path_check(state: CaseState) -> str:
    """Skip critic for fast-path cases (simple, low-risk queries)."""
    if state.get("fast_path", False):
        return "guardrail_gate"
    return "critic"


def route_after_guardrail(state: CaseState) -> str:
    """
    After guardrail gate: route based on autonomy level.
    
    KEY CONCEPT - Human-in-the-Loop:
    For approval-required cases, we go to a "human_review" node
    that uses LangGraph's interrupt mechanism. The graph literally
    PAUSES and waits for a human to approve/edit/reject.
    """
    autonomy = state.get("autonomy_level", "escalate")
    
    if autonomy == "auto_resolve":
        return "responder"
    elif autonomy == "human_approval":
        return "human_review"
    else:  # escalate
        return "responder"


# ============================================================
# Human Review Node (interrupt point)
# ============================================================

async def human_review_node(state: CaseState) -> dict:
    """
    This node is where the graph PAUSES for human approval.
    
    KEY CONCEPT - Graph Interrupts:
    LangGraph can pause execution at any node. The graph state
    is saved (checkpointed), and execution stops. When a human
    approves via the dashboard, we resume the graph from this
    exact point with the human's decision injected into state.
    
    In this implementation, we handle it via the API: the case
    is saved with status "awaiting_approval" and the frontend
    shows it in the approval queue.
    """
    return {
        "awaiting_human": True,
        "status": "awaiting_approval",
        "current_node": "human_review",
        "trace_events": [{
            "timestamp": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "node": "human_review",
            "event_type": "interrupt",
            "data": {
                "message": "Awaiting supervisor approval",
                "resolution_type": state.get("resolution_type", ""),
                "amount": state.get("resolution_amount", 0),
                "confidence": state.get("resolution_confidence", 0),
            },
        }],
    }


# ============================================================
# Build the Graph
# ============================================================

def build_agent_graph():
    """
    Construct the complete LangGraph agent graph.
    
    KEY CONCEPT - Graph Construction:
    1. Create a StateGraph with our CaseState type
    2. Add nodes (processing steps)
    3. Add edges (connections between steps)
    4. Add conditional edges (branching logic)
    5. Compile with a checkpointer (enables pause/resume)
    
    The compiled graph is an executable that takes state and runs
    the nodes in the correct order based on the edges.
    """
    
    # Create graph with our state type
    graph = StateGraph(CaseState)
    
    # --- Add all nodes ---
    graph.add_node("intake", intake_node)
    graph.add_node("triage", triage_node)
    graph.add_node("planner", planner_node)
    graph.add_node("tools", tools_node)
    graph.add_node("reasoner", reasoner_node)
    graph.add_node("critic", critic_node)
    graph.add_node("guardrail_gate", guardrail_gate_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("responder", responder_node)
    graph.add_node("logger", logger_node)
    
    # --- Set entry point ---
    graph.set_entry_point("intake")
    
    # --- Add edges ---
    
    # After intake: check for injection
    graph.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "blocked": "responder",   # Injection → blocked response
            "triage": "triage",       # Safe → continue
        }
    )
    
    # After triage: check for missing info
    graph.add_conditional_edges(
        "triage",
        route_after_triage,
        {
            "ask_info": "responder",  # Missing info → ask customer
            "planner": "planner",     # Complete → plan tools
        }
    )
    
    # Planner → Tools (always)
    graph.add_edge("planner", "tools")
    
    # Tools → Reasoner (always)
    graph.add_edge("tools", "reasoner")
    
    # After reasoner: fast path skips critic
    graph.add_conditional_edges(
        "reasoner",
        route_after_fast_path_check,
        {
            "critic": "critic",
            "guardrail_gate": "guardrail_gate",
        }
    )
    
    # After critic: pass/fail/retry
    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "guardrail_gate": "guardrail_gate",  # Passed or max retries
            "reasoner_retry": "reasoner",         # Failed, retry
        }
    )
    
    # After guardrail: auto/approval/escalate
    graph.add_conditional_edges(
        "guardrail_gate",
        route_after_guardrail,
        {
            "responder": "responder",         # Auto-resolve or escalate
            "human_review": "human_review",   # Needs approval
        }
    )
    
    # Human review → responder
    graph.add_edge("human_review", "responder")
    
    # Responder → Logger (always)
    graph.add_edge("responder", "logger")
    
    # Logger → END
    graph.add_edge("logger", END)
    
    # --- Compile with checkpointer ---
    # The MemorySaver checkpointer stores graph state in memory,
    # enabling pause/resume for human-in-the-loop.
    # For production, use SqliteSaver or PostgresSaver.
    checkpointer = MemorySaver()
    
    compiled = graph.compile(checkpointer=checkpointer)
    
    return compiled


# ============================================================
# Global Graph Instance
# ============================================================

_agent_graph = None


def get_agent_graph():
    """Get or create the singleton agent graph."""
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph
