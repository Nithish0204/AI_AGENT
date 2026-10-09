"""
REASONER Node: Making the Decision
=====================================

This is the "brain" of the agent. It combines:
- Policy evidence from the knowledge base
- Order facts from the database
- Customer history
- Refund eligibility (computed by code)

...and produces a structured decision with citations.

KEY CONCEPT - Retrieval-Augmented Generation (RAG):
The LLM doesn't rely on its training data for policy details.
Instead, we RETRIEVE relevant policy documents and INJECT them
into the prompt. The LLM then GENERATES a decision grounded
in those documents. This is RAG — and it's how we prevent
hallucination about policies.
"""

import time
import json
from datetime import datetime, timezone

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from app.agent.state import CaseState
from app.agent.prompts import REASONER_PROMPT
from app.models.schemas import ReasonerDecision
from app.config import get_settings


def _format_policy_evidence(policies: list[dict]) -> str:
    """Format retrieved policy chunks for the prompt."""
    if not policies:
        return "No relevant policies found."
    
    parts = []
    for i, p in enumerate(policies, 1):
        source = p.get("source", "unknown")
        section = p.get("section", "")
        score = p.get("score", 0)
        text = p.get("text", "")
        parts.append(
            f"### Policy {i} (source: {source}, section: {section}, relevance: {score:.2f})\n{text}"
        )
    return "\n\n".join(parts)


def _format_data(data: dict | None, label: str) -> str:
    """Format tool result data for the prompt."""
    if not data:
        return f"No {label} available."
    return json.dumps(data, indent=2, default=str)


async def reasoner_node(state: CaseState) -> dict:
    """
    Combine all evidence and produce a resolution decision.
    
    KEY CONCEPT - Grounded Reasoning:
    Every claim the reasoner makes must be backed by a citation.
    We enforce this through:
    1. The prompt explicitly requires citations
    2. The Pydantic schema requires a citations list
    3. The CRITIC node will verify each citation (next step)
    
    This three-layer approach catches hallucinations.
    """
    start_time = time.time()
    settings = get_settings()
    
    # Use the stronger model for reasoning
    llm = ChatGoogleGenerativeAI(
        model=settings.reasoning_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.2,  # Slightly creative for reasoning, but mostly deterministic
    )
    
    structured_llm = llm.with_structured_output(ReasonerDecision)
    
    # Format all evidence for the prompt
    policy_evidence = _format_policy_evidence(state.get("retrieved_policies", []))
    order_data = _format_data(state.get("order_data"), "order data")
    shipment_data = _format_data(state.get("shipment_data"), "shipment data")
    customer_history = _format_data(state.get("customer_history"), "customer history")
    refund_eligibility = _format_data(state.get("refund_eligibility"), "refund eligibility")
    
    # If critic had issues before, include that feedback
    critic_feedback = ""
    if state.get("critic_issues"):
        critic_feedback = (
            "\n## IMPORTANT: Previous attempt had these issues (fix them!):\n" +
            "\n".join(f"- {issue}" for issue in state["critic_issues"])
        )
    
    prompt = REASONER_PROMPT.format(
        triage_summary=state.get("triage_summary", ""),
        intents=state.get("intents", []),
        sentiment=state.get("sentiment", "neutral"),
        urgency=state.get("urgency", "medium"),
        policy_evidence=policy_evidence,
        order_data=order_data,
        shipment_data=shipment_data,
        customer_history=customer_history,
        refund_eligibility=refund_eligibility,
    )
    
    if critic_feedback:
        prompt += critic_feedback
    
    try:
        result: ReasonerDecision = await structured_llm.ainvoke([HumanMessage(content=prompt)])
        
        # SAFETY CHECK: If code says refund ineligible, override LLM's decision
        refund_elig = state.get("refund_eligibility")
        if (refund_elig and not refund_elig.get("eligible") and 
            result.resolution_type.value == "refund" and result.amount > 0):
            # LLM tried to give a refund despite code saying no — block it
            result = ReasonerDecision(
                resolution_type="escalate",
                amount=0,
                reasoning=(
                    f"Original decision was refund of ₹{result.amount}, but refund eligibility "
                    f"check (code-based, authoritative) blocked it: "
                    f"{', '.join(refund_elig.get('blockers', []))}. Escalating for human review."
                ),
                citations=result.citations,
                confidence=0.5,
                risk_level="high",
            )
        
        duration = (time.time() - start_time) * 1000
        
        trace_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node": "reasoner",
            "event_type": "node_complete",
            "data": {
                "resolution_type": result.resolution_type.value,
                "amount": result.amount,
                "confidence": result.confidence,
                "risk_level": result.risk_level.value,
                "citations_count": len(result.citations),
                "reasoning_preview": result.reasoning[:200] + "..." if len(result.reasoning) > 200 else result.reasoning,
            },
            "duration_ms": round(duration, 2),
        }
        
        return {
            "resolution_type": result.resolution_type.value,
            "resolution_amount": result.amount,
            "resolution_reasoning": result.reasoning,
            "resolution_citations": [c.model_dump() for c in result.citations],
            "resolution_confidence": result.confidence,
            "risk_level": result.risk_level.value,
            "current_node": "reasoner",
            "trace_events": [trace_event],
        }
    
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return {
            "resolution_type": "escalate",
            "resolution_amount": 0,
            "resolution_reasoning": f"Reasoning failed: {str(e)}. Escalating for human review.",
            "resolution_citations": [],
            "resolution_confidence": 0.0,
            "risk_level": "critical",
            "current_node": "reasoner",
            "trace_events": [{
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node": "reasoner",
                "event_type": "error",
                "data": {"error": str(e)},
                "duration_ms": round(duration, 2),
            }],
        }
