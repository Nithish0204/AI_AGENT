"""
CRITIC Node: Independent Verification
=======================================

The critic is a SEPARATE LLM call that acts as a fact-checker.
It reads the reasoner's output and verifies every claim against
the actual evidence.

KEY CONCEPT - Self-Verification / Reflection:
Having one LLM call "check" another's work catches errors:
- Hallucinated policies ("our policy states..." when it doesn't)
- Wrong amounts ("the order was $X" when it was $Y)
- Unsupported conclusions ("therefore eligible" without evidence)

This is like having a second pair of eyes review a decision.
On failure, we retry ONCE with feedback, then escalate.
"""

import time
from datetime import datetime, timezone

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from app.agent.state import CaseState
from app.agent.prompts import CRITIC_PROMPT
from app.models.schemas import CriticVerification
from app.config import get_settings


def _format_citations(citations: list[dict]) -> str:
    """Format citations for the critic prompt."""
    if not citations:
        return "No citations provided."
    parts = []
    for i, c in enumerate(citations, 1):
        parts.append(
            f"{i}. Source: {c.get('source', 'unknown')}, "
            f"Section: {c.get('section', 'N/A')}\n"
            f"   Quote: \"{c.get('quote', 'N/A')}\""
        )
    return "\n".join(parts)


def _format_policy_evidence(policies: list[dict]) -> str:
    """Format retrieved policies for verification."""
    if not policies:
        return "No policies available."
    parts = []
    for i, p in enumerate(policies, 1):
        parts.append(f"Policy {i} ({p.get('source', 'unknown')}):\n{p.get('text', '')}")
    return "\n\n".join(parts)


async def critic_node(state: CaseState) -> dict:
    """
    Verify the reasoner's decision against actual evidence.
    
    KEY CONCEPT - Groundedness Check:
    For each claim in the reasoning, we ask: "Does the evidence
    actually support this?" If not, we flag it. This prevents
    the agent from making decisions based on hallucinated information.
    
    Flow:
    1. First attempt → critic checks → pass or fail
    2. If fail + retry_count < max → go back to reasoner with feedback
    3. If fail + retry_count >= max → escalate to human
    """
    start_time = time.time()
    settings = get_settings()
    
    # Track retry count
    retry_count = state.get("critic_retry_count", 0)
    
    llm = ChatGoogleGenerativeAI(
        model=settings.reasoning_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.0,  # Critic should be completely deterministic
    )
    
    structured_llm = llm.with_structured_output(CriticVerification)
    
    # Format previous critic feedback if this is a retry
    critic_feedback = ""
    if state.get("critic_issues"):
        critic_feedback = (
            "\n## PREVIOUS ISSUES (these should now be fixed):\n" +
            "\n".join(f"- {issue}" for issue in state["critic_issues"])
        )
    
    prompt = CRITIC_PROMPT.format(
        resolution_type=state.get("resolution_type", ""),
        resolution_amount=state.get("resolution_amount", 0),
        resolution_confidence=state.get("resolution_confidence", 0),
        resolution_reasoning=state.get("resolution_reasoning", ""),
        resolution_citations=_format_citations(state.get("resolution_citations", [])),
        policy_evidence=_format_policy_evidence(state.get("retrieved_policies", [])),
        order_data=str(state.get("order_data", "No order data")),
        customer_history=str(state.get("customer_history", "No customer history")),
        critic_feedback=critic_feedback,
    )
    
    try:
        result: CriticVerification = await structured_llm.ainvoke([HumanMessage(content=prompt)])
        
        duration = (time.time() - start_time) * 1000
        
        trace_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node": "critic",
            "event_type": "node_complete",
            "data": {
                "passed": result.passed,
                "groundedness_score": result.groundedness_score,
                "issues": result.issues,
                "suggestions": result.suggestions,
                "retry_count": retry_count,
            },
            "duration_ms": round(duration, 2),
        }
        
        return {
            "critic_passed": result.passed,
            "critic_issues": result.issues,
            "critic_retry_count": retry_count + (0 if result.passed else 1),
            "current_node": "critic",
            "trace_events": [trace_event],
        }
    
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        # If critic fails, be conservative — don't pass
        return {
            "critic_passed": False,
            "critic_issues": [f"Critic error: {str(e)}"],
            "critic_retry_count": retry_count + 1,
            "current_node": "critic",
            "trace_events": [{
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node": "critic",
                "event_type": "error",
                "data": {"error": str(e)},
                "duration_ms": round(duration, 2),
            }],
        }
