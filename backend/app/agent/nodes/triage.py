"""
TRIAGE Node: Understanding What the Customer Needs
====================================================

This node uses an LLM with structured output to extract:
- Intents (what the customer wants — can be multiple)
- Order ID (if mentioned)
- Sentiment (how they feel)
- Urgency (how urgent this is)
- Missing info (what we still need to know)
- Confidence (how sure we are about this analysis)

KEY CONCEPT - Structured Output:
Instead of getting free-form text and parsing it, we tell the LLM
"return a JSON object matching this exact schema." LangChain's
`with_structured_output()` uses function calling or JSON mode
to guarantee we get valid, typed data back.
"""

import time
from datetime import datetime, timezone

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from app.agent.state import CaseState
from app.agent.prompts import TRIAGE_PROMPT
from app.models.schemas import TriageResult
from app.config import get_settings


async def triage_node(state: CaseState) -> dict:
    """
    Analyze the customer message and extract structured triage information.
    
    KEY CONCEPT - LLM with Structured Output:
    We create the LLM, call `.with_structured_output(TriageResult)`,
    which tells the model to return JSON matching our Pydantic schema.
    The result is a validated Python object, not a string.
    
    This is more reliable than asking the LLM to "return JSON" in the prompt
    because it uses the model's native structured output mode.
    """
    start_time = time.time()
    settings = get_settings()
    
    # Use the fast model for triage (it's a simpler task)
    llm = ChatGoogleGenerativeAI(
        model=settings.fast_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.1,  # Low temperature for consistent extraction
    )
    
    # Bind the Pydantic schema — the LLM will return a TriageResult object
    structured_llm = llm.with_structured_output(TriageResult)
    
    # Use the PII-redacted message (never send raw PII to the LLM)
    message = state.get("pii_redacted_message", state.get("customer_message", ""))
    if state.get("detected_language", "en") != "en" and state.get("translated_message"):
        message = state["translated_message"]
    
    # Format the prompt with context
    prompt = TRIAGE_PROMPT.format(
        customer_id=state.get("customer_id", "unknown"),
        customer_tier=state.get("customer_tier", "standard"),
        message=message,
        conversation_history=state.get("conversation_history", []),
    )
    
    try:
        # Invoke the LLM — result is a TriageResult Pydantic object
        result: TriageResult = await structured_llm.ainvoke([HumanMessage(content=prompt)])
        
        duration = (time.time() - start_time) * 1000
        
        trace_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node": "triage",
            "event_type": "node_complete",
            "data": {
                "intents": result.intents,
                "order_id": result.order_id,
                "sentiment": result.sentiment.value,
                "urgency": result.urgency.value,
                "summary": result.summary,
                "missing_info": result.missing_info,
                "confidence": result.confidence,
            },
            "duration_ms": round(duration, 2),
        }
        
        return {
            "intents": result.intents,
            "order_id": result.order_id or "",
            "sentiment": result.sentiment.value,
            "urgency": result.urgency.value,
            "missing_info": result.missing_info,
            "triage_confidence": result.confidence,
            "triage_summary": result.summary,
            "current_node": "triage",
            "trace_events": [trace_event],
        }
    
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        
        # Graceful degradation — if triage fails, use safe defaults
        return {
            "intents": ["general_inquiry"],
            "order_id": "",
            "sentiment": "neutral",
            "urgency": "medium",
            "missing_info": [],
            "triage_confidence": 0.3,
            "triage_summary": f"Triage failed: {str(e)}",
            "current_node": "triage",
            "trace_events": [{
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node": "triage",
                "event_type": "error",
                "data": {"error": str(e)},
                "duration_ms": round(duration, 2),
            }],
        }
