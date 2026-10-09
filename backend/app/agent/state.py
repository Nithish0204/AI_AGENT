"""
CaseState: The Central Nervous System of the Agent
===================================================

KEY CONCEPT - Agent State:
In LangGraph, the agent's "memory" during a single case is a typed dictionary
called "state". Every node in the graph receives this state, reads what it needs,
does its work, and returns updates. The LangGraph runtime merges those updates
back into the state before passing it to the next node.

Think of it like a medical chart that travels with a patient through different
departments in a hospital. Each department reads the chart, adds their findings,
and passes it along.

WHY TypedDict (not a Pydantic model)?
- LangGraph nodes return PARTIAL updates (only changed fields)
- TypedDict with total=False allows this naturally
- Pydantic would require returning the full model every time
- TypedDict is also more memory-efficient for large state

KEY CONCEPT - Reducers (Annotated fields):
When multiple nodes update the same field, LangGraph needs to know HOW to merge.
For example, trace_events should APPEND (not replace). We use Annotated with a
reducer function to specify the merge strategy.
"""

from typing import TypedDict, Annotated, Any
import operator


# ============================================================
# Custom Reducers
# ============================================================

def merge_lists(left: list | None, right: list | None) -> list:
    """
    Reducer that appends new items to an existing list.
    Used for trace_events and other accumulating fields.
    
    Example:
        State has trace_events: [event1, event2]
        Node returns trace_events: [event3]
        After merge: trace_events: [event1, event2, event3]
    """
    left = left or []
    right = right or []
    return left + right


def merge_dicts(left: dict | None, right: dict | None) -> dict:
    """Reducer that merges dictionaries (right overwrites left on conflicts)."""
    left = left or {}
    right = right or {}
    return {**left, **right}


# ============================================================
# CaseState Definition
# ============================================================

class CaseState(TypedDict, total=False):
    """
    Complete state for a customer support case flowing through the agent graph.
    
    `total=False` means all fields are optional — nodes only return the fields
    they update, and LangGraph handles merging them into the full state.
    
    Fields are grouped by the node that primarily writes them.
    """
    
    # ========== INPUT (set when case is created) ==========
    case_id: str                                    # Unique case identifier
    customer_id: str                                # Verified customer ID
    customer_message: str                           # Raw customer input
    conversation_history: list[dict[str, Any]]      # Previous turns in this case
    
    # ========== INTAKE NODE ==========
    detected_language: str                          # ISO 639-1: "en", "te", "hi"
    original_language_message: str                  # Preserved original
    translated_message: str                         # English translation (if input was non-English)
    pii_redacted_message: str                       # Message with PII masked: "My SSN is <REDACTED>"
    pii_entities_found: list[dict[str, Any]]        # [{type: "PHONE", start: 10, end: 20}]
    injection_detected: bool                        # Was prompt injection detected?
    injection_score: float                          # 0.0 - 1.0, higher = more likely injection
    injection_details: str                          # Why it was flagged
    
    # ========== TRIAGE NODE ==========
    intents: list[str]                              # ["refund_request", "delivery_complaint"]
    order_id: str                                   # Extracted order ID (e.g., "ORD-1234")
    sentiment: str                                  # "angry" | "frustrated" | "neutral" | "positive"
    urgency: str                                    # "critical" | "high" | "medium" | "low"
    customer_tier: str                              # "vip" | "premium" | "standard"
    missing_info: list[str]                         # ["order_id", "product_name"]
    triage_confidence: float                        # 0.0 - 1.0
    triage_summary: str                             # "Customer wants refund for late delivery"
    
    # ========== PLANNER NODE ==========
    execution_plan: list[str]                       # ["search_knowledge_base", "get_order"]
    fast_path: bool                                 # True = simple case, skip some steps
    
    # ========== TOOL RESULTS ==========
    order_data: dict[str, Any] | None               # Order details from DB
    customer_history: dict[str, Any] | None         # Past cases, orders, refund history
    shipment_data: dict[str, Any] | None            # Carrier tracking info
    refund_eligibility: dict[str, Any] | None       # Computed eligibility (code, not LLM)
    retrieved_policies: list[dict[str, Any]]        # Policy chunks with similarity scores
    
    # ========== REASONER NODE ==========
    resolution_type: str                            # "refund" | "replacement" | "compensation" | ...
    resolution_amount: float                        # Dollar amount (0 if N/A)
    resolution_reasoning: str                       # Step-by-step reasoning chain
    resolution_citations: list[dict[str, Any]]      # [{source: "refund_policy.md", quote: "..."}]
    resolution_confidence: float                    # 0.0 - 1.0
    risk_level: str                                 # "low" | "medium" | "high" | "critical"
    
    # ========== CRITIC NODE ==========
    critic_passed: bool                             # Did the critic approve?
    critic_issues: list[str]                        # ["Claim X not supported by evidence"]
    critic_retry_count: int                         # How many times we've retried
    
    # ========== GUARDRAIL GATE (pure code, not LLM) ==========
    autonomy_level: str                             # "auto_resolve" | "human_approval" | "escalate"
    guardrail_reasons: list[str]                    # ["confidence 0.92 >= 0.85", "amount $50 <= $2000"]
    fraud_flags: list[str]                          # ["3 refunds in 30 days", "address mismatch"]
    
    # ========== HUMAN-IN-THE-LOOP ==========
    awaiting_human: bool                            # Is the graph paused for human input?
    human_decision: str | None                      # "approved" | "edited" | "rejected"
    human_notes: str | None                         # Supervisor's notes
    human_modified_resolution: dict[str, Any] | None  # If supervisor edited the resolution
    
    # ========== RESPONDER NODE ==========
    response_text: str                              # Final customer-facing response
    response_language: str                          # Language of the response
    
    # ========== OBSERVABILITY ==========
    # These use reducers so each node APPENDS rather than replacing
    trace_events: Annotated[list[dict[str, Any]], merge_lists]  # Full trace log
    current_node: str                               # Which node is running right now
    total_tokens: int                               # Running token count
    total_cost: float                               # Running cost estimate ($)
    node_latencies: Annotated[dict[str, float], merge_dicts]  # node_name -> seconds
    
    # ========== CASE METADATA ==========
    created_at: str                                 # ISO timestamp
    updated_at: str                                 # ISO timestamp
    status: str                                     # "processing" | "resolved" | "escalated" | "awaiting_approval" | "blocked"
    error: str | None                               # Error message if something went wrong
