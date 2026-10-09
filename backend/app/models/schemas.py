"""
Pydantic Schemas: Structured Outputs & API Models
==================================================

KEY CONCEPT - Structured Outputs:
Instead of asking the LLM to return free-form text and parsing it with regex,
we define Pydantic models that describe the EXACT shape of the output we want.
LangChain's `with_structured_output(MyModel)` tells the LLM to return JSON
matching our schema. Pydantic then validates it automatically.

Why this matters:
1. Type safety — you get Python objects, not strings
2. Validation — Pydantic catches missing/wrong fields
3. Documentation — the schema IS the documentation
4. Reliability — structured output mode uses constrained decoding
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from enum import Enum


# ============================================================
# Enums for constrained values
# ============================================================

class Sentiment(str, Enum):
    ANGRY = "angry"
    FRUSTRATED = "frustrated"
    NEUTRAL = "neutral"
    POSITIVE = "positive"


class Urgency(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CustomerTier(str, Enum):
    VIP = "vip"
    PREMIUM = "premium"
    STANDARD = "standard"


class ResolutionType(str, Enum):
    REFUND = "refund"
    REPLACEMENT = "replacement"
    COMPENSATION = "compensation"
    INFORMATION = "information"
    APOLOGY = "apology"
    ESCALATE = "escalate"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AutonomyLevel(str, Enum):
    AUTO_RESOLVE = "auto_resolve"
    HUMAN_APPROVAL = "human_approval"
    ESCALATE = "escalate"


class CaseStatus(str, Enum):
    PROCESSING = "processing"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    AWAITING_APPROVAL = "awaiting_approval"
    BLOCKED = "blocked"


# ============================================================
# Structured LLM Output Schemas
# ============================================================

class TriageResult(BaseModel):
    """
    Structured output from the TRIAGE node.
    The LLM extracts structured information from the customer's raw message.
    
    KEY CONCEPT - Intent Extraction:
    A customer message like "Where is my order ORD-123? I want a refund!"
    contains TWO intents: order_status_inquiry AND refund_request.
    We extract all of them so the planner can handle each.
    """
    intents: list[str] = Field(
        description="List of detected customer intents. Examples: "
        "'refund_request', 'delivery_complaint', 'order_status', "
        "'cancellation', 'payment_issue', 'product_quality', 'general_inquiry'"
    )
    order_id: Optional[str] = Field(
        default=None,
        description="Extracted order ID if mentioned (e.g., 'ORD-1234'). None if not found."
    )
    sentiment: Sentiment = Field(
        description="Overall customer sentiment"
    )
    urgency: Urgency = Field(
        description="Urgency level based on issue severity and customer tone"
    )
    summary: str = Field(
        description="One-sentence summary of what the customer needs"
    )
    missing_info: list[str] = Field(
        default_factory=list,
        description="Information needed but not provided (e.g., 'order_id', 'product_name')"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in the triage assessment (0.0 to 1.0)"
    )


class Citation(BaseModel):
    """A reference to a specific piece of evidence supporting a claim."""
    source: str = Field(description="Document name or data source (e.g., 'refund_policy.md')")
    section: str = Field(default="", description="Section heading within the document")
    quote: str = Field(description="Exact quote or data point supporting the claim")
    relevance: float = Field(
        ge=0.0, le=1.0, default=1.0,
        description="How relevant this citation is to the decision"
    )


class ReasonerDecision(BaseModel):
    """
    Structured output from the REASONER node.
    Combines policy evidence + order facts + customer history into a decision.
    
    KEY CONCEPT - Explainable AI:
    Every field here serves explainability. The reasoning field shows the
    chain of thought. Citations prove each claim. Confidence lets the
    guardrail gate make deterministic decisions.
    """
    resolution_type: ResolutionType = Field(
        description="What action to take for the customer"
    )
    amount: float = Field(
        default=0.0, ge=0.0,
        description="Monetary amount for refund/compensation (0 if not applicable)"
    )
    reasoning: str = Field(
        description="Step-by-step reasoning explaining why this decision was made, "
        "referencing specific policies and order facts"
    )
    citations: list[Citation] = Field(
        description="Evidence supporting the decision — every claim must have a citation"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in this decision (0.0 to 1.0)"
    )
    risk_level: RiskLevel = Field(
        description="Risk level considering amount, policy clarity, and edge cases"
    )


class CriticVerification(BaseModel):
    """
    Structured output from the CRITIC node.
    An independent check that verifies the reasoner's claims against evidence.
    
    KEY CONCEPT - Self-Verification:
    The critic is a SEPARATE LLM call that acts as a fact-checker. It reads
    the reasoner's output and checks every claim against the actual retrieved
    documents and order data. This catches hallucinations.
    """
    passed: bool = Field(
        description="Whether all claims are supported by evidence"
    )
    issues: list[str] = Field(
        default_factory=list,
        description="List of specific issues found (unsupported claims, contradictions)"
    )
    groundedness_score: float = Field(
        ge=0.0, le=1.0,
        description="What fraction of claims are grounded in evidence (0.0 to 1.0)"
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Suggestions for fixing the issues"
    )


class PlannerResult(BaseModel):
    """Output from the PLANNER node — which tools to call and in what order."""
    tools_needed: list[str] = Field(
        description="List of tool names to execute. Options: "
        "'search_knowledge_base', 'get_order', 'get_customer_history', "
        "'check_shipment_status', 'check_refund_eligibility'"
    )
    fast_path: bool = Field(
        description="True if this is a simple case that can skip the critic step"
    )
    reasoning: str = Field(
        description="Brief explanation of why these tools are needed"
    )


# ============================================================
# API Request / Response Schemas
# ============================================================

class ChatRequest(BaseModel):
    """Incoming chat message from a customer."""
    message: str = Field(min_length=1, max_length=5000, description="Customer's message")
    customer_id: str = Field(description="Authenticated customer ID")
    case_id: Optional[str] = Field(
        default=None,
        description="Existing case ID for follow-up messages. None for new cases."
    )


class TraceEvent(BaseModel):
    """A single event in the agent's execution trace — sent via SSE to the frontend."""
    timestamp: str
    node: str                           # Which graph node generated this
    event_type: str                     # "node_start", "node_end", "tool_call", "llm_call", "guardrail", "decision"
    data: dict[str, Any] = Field(default_factory=dict)  # Event-specific payload
    duration_ms: Optional[float] = None
    tokens_used: Optional[int] = None


class CaseResponse(BaseModel):
    """Full case details returned by the API."""
    case_id: str
    customer_id: str
    status: str
    customer_message: str
    response_text: Optional[str] = None
    resolution_type: Optional[str] = None
    resolution_amount: Optional[float] = None
    autonomy_level: Optional[str] = None
    confidence: Optional[float] = None
    detected_language: Optional[str] = None
    trace_events: list[TraceEvent] = Field(default_factory=list)
    created_at: str
    updated_at: Optional[str] = None


class ApprovalRequest(BaseModel):
    """Supervisor's decision on a case requiring human approval."""
    decision: str = Field(
        description="'approved', 'edited', or 'rejected'"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Supervisor's notes explaining the decision"
    )
    modified_resolution_type: Optional[str] = None
    modified_amount: Optional[float] = None
    modified_response: Optional[str] = None


class DashboardStats(BaseModel):
    """Analytics data for the supervisor dashboard."""
    total_cases: int = 0
    auto_resolved: int = 0
    human_approved: int = 0
    escalated: int = 0
    blocked: int = 0
    avg_response_time_ms: float = 0.0
    avg_cost_per_case: float = 0.0
    auto_resolution_rate: float = 0.0
    escalation_rate: float = 0.0
    top_intents: list[dict[str, Any]] = Field(default_factory=list)
    estimated_hours_saved: float = 0.0
    estimated_cost_saved: float = 0.0
