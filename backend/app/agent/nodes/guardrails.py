"""
GUARDRAIL GATE Node: The Final Safety Check
=============================================

This is PURE CODE — no LLM involved. It's the final authority
on what the agent can do autonomously.

KEY CONCEPT - Deterministic Guardrails:
The LLM proposes, but CODE disposes. No matter how confident
the LLM is, or how convincing a prompt injection might be,
this node makes the final call using hard-coded rules:

  AUTO-RESOLVE:  confidence >= 0.85 AND amount <= ₹2000 AND critic passed
  HUMAN APPROVAL: 0.60 <= confidence < 0.85 OR ₹2000 < amount <= ₹10000
  ESCALATE:      confidence < 0.60 OR amount > ₹10000 OR fraud flags

Why is this code, not AI?
Because a clever attacker could manipulate an LLM-based guardrail.
They CANNOT manipulate a Python if-statement.
"""

import time
from datetime import datetime, timezone

from app.agent.state import CaseState
from app.config import get_settings


# Keywords that always trigger escalation (safety-critical)
ESCALATION_KEYWORDS = [
    "legal", "lawyer", "attorney", "court", "lawsuit", "sue",
    "fraud", "scam", "stolen", "identity theft",
    "threat", "harm", "dangerous", "safety", "hazard",
    "media", "news", "social media", "twitter", "review bomb",
    "regulatory", "consumer court", "ombudsman",
    "police", "FIR", "complaint against company",
]


async def guardrail_gate_node(state: CaseState) -> dict:
    """
    Determine the autonomy level using deterministic business rules.
    
    This node examines:
    1. Confidence score from the reasoner
    2. Resolution amount
    3. Critic pass/fail
    4. Fraud flags from customer history
    5. Safety keywords in the original message
    6. Customer tier (VIP gets different handling)
    
    Returns the autonomy_level and detailed reasons for the decision.
    Every decision is logged with its reasoning for audit.
    """
    start_time = time.time()
    settings = get_settings()
    
    confidence = state.get("resolution_confidence", 0.0)
    amount = state.get("resolution_amount", 0.0)
    critic_passed = state.get("critic_passed", False)
    customer_tier = state.get("customer_tier", "standard")
    sentiment = state.get("sentiment", "neutral")
    message = state.get("customer_message", "").lower()
    
    reasons = []
    fraud_flags = []
    
    # ============================================================
    # Check for ESCALATION triggers (highest priority)
    # ============================================================
    
    # Safety keywords in message
    for keyword in ESCALATION_KEYWORDS:
        if keyword in message:
            reasons.append(f"Escalation keyword detected: '{keyword}'")
    
    # Fraud check: too many recent refunds
    customer_history = state.get("customer_history")
    if customer_history:
        recent_refunds = customer_history.get("refunds_last_30_days", 0)
        if recent_refunds >= settings.max_refund_claims_30_days:
            fraud_flags.append(
                f"High refund frequency: {recent_refunds} refunds in 30 days "
                f"(threshold: {settings.max_refund_claims_30_days})"
            )
    
    # Refund eligibility blockers
    refund_elig = state.get("refund_eligibility")
    if refund_elig and not refund_elig.get("eligible") and amount > 0:
        fraud_flags.append(f"Refund blocked by eligibility check: {refund_elig.get('blockers', [])}")
    
    # Order not found but customer claims to have one
    if state.get("order_id") and not state.get("order_data"):
        reasons.append("Order not found in database — possible data mismatch")
    
    # No relevant policy found
    if not state.get("retrieved_policies"):
        reasons.append("No relevant policy documents found for this issue")
    
    # Critic failed too many times
    critic_retry_count = state.get("critic_retry_count", 0)
    if critic_retry_count >= settings.max_critic_retries and not critic_passed:
        reasons.append(f"Critic failed {critic_retry_count} times — groundedness unverified")
    
    # VIP + high value = always needs human
    if customer_tier == "vip" and amount > 5000:
        reasons.append(f"VIP customer with high-value resolution (₹{amount:.0f})")
    
    # Angry sentiment unresolved
    if sentiment == "angry" and state.get("resolution_type") not in ("refund", "replacement"):
        reasons.append("Angry customer — resolution may not adequately address frustration")
    
    # ============================================================
    # Determine autonomy level
    # ============================================================
    
    # ESCALATE conditions (any one triggers)
    escalate = (
        len(reasons) > 2 or  # Multiple escalation signals
        amount > settings.human_approval_max_amount or
        any("fraud" in r.lower() or "legal" in r.lower() for r in reasons) or
        len(fraud_flags) > 0 or
        confidence < 0.3 or
        (critic_retry_count >= settings.max_critic_retries and not critic_passed) or
        state.get("resolution_type") == "escalate"
    )
    
    # AUTO-RESOLVE conditions (ALL must be true)
    auto_resolve = (
        not escalate and
        confidence >= settings.auto_resolve_confidence and
        amount <= settings.auto_resolve_max_amount and
        critic_passed and
        len(fraud_flags) == 0 and
        len(reasons) == 0 and
        customer_tier != "vip"  # VIP always gets human touch
    )
    
    # Everything else needs human approval
    if escalate:
        autonomy_level = "escalate"
        reasons.append(f"ESCALATED: amount=₹{amount:.0f}, confidence={confidence:.2f}")
    elif auto_resolve:
        autonomy_level = "auto_resolve"
        reasons = [
            f"confidence {confidence:.2f} >= {settings.auto_resolve_confidence}",
            f"amount ₹{amount:.0f} <= ₹{settings.auto_resolve_max_amount:.0f}",
            "critic passed",
            "no fraud flags",
        ]
    else:
        autonomy_level = "human_approval"
        if not reasons:
            reasons = [
                f"confidence {confidence:.2f} (threshold: {settings.auto_resolve_confidence})",
                f"amount ₹{amount:.0f} (auto-resolve max: ₹{settings.auto_resolve_max_amount:.0f})",
                f"critic passed: {critic_passed}",
            ]
    
    duration = (time.time() - start_time) * 1000
    
    # Map to case status
    status_map = {
        "auto_resolve": "resolved",
        "human_approval": "awaiting_approval",
        "escalate": "escalated",
    }
    
    trace_event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "guardrail_gate",
        "event_type": "node_complete",
        "data": {
            "autonomy_level": autonomy_level,
            "reasons": reasons,
            "fraud_flags": fraud_flags,
            "confidence": confidence,
            "amount": amount,
            "critic_passed": critic_passed,
        },
        "duration_ms": round(duration, 2),
    }
    
    return {
        "autonomy_level": autonomy_level,
        "guardrail_reasons": reasons,
        "fraud_flags": fraud_flags,
        "status": status_map.get(autonomy_level, "processing"),
        "awaiting_human": autonomy_level == "human_approval",
        "current_node": "guardrail_gate",
        "trace_events": [trace_event],
    }
