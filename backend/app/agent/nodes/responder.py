"""
RESPONDER Node: Crafting the Customer's Reply
===============================================

This node generates the final customer-facing response.
It translates back to the customer's language if needed.

KEY CONCEPT - Tone Adaptation:
The response tone adapts to the customer's emotional state:
- Angry → Empathetic acknowledgment + clear resolution
- Frustrated → Understanding + proactive next steps
- Neutral → Professional + informative
- Positive → Warm + reinforcing

The agent should feel human, not robotic.
"""

import time
from datetime import datetime, timezone

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from app.agent.state import CaseState
from app.agent.prompts import RESPONDER_PROMPT
from app.config import get_settings


async def responder_node(state: CaseState) -> dict:
    """
    Generate the final customer-facing response.
    
    This is the LAST node the customer sees. It must:
    1. Be empathetic and professional
    2. Clearly communicate the resolution
    3. Be in the customer's language
    4. NEVER reveal internal details (confidence scores, tool names, etc.)
    """
    start_time = time.time()
    settings = get_settings()
    
    # Determine response language
    detected_lang = state.get("detected_language", "en")
    lang_names = {"en": "English", "te": "Telugu", "hi": "Hindi", "mr": "Marathi", "ta": "Tamil"}
    response_language = lang_names.get(detected_lang, "English")
    
    # Build status details based on autonomy level
    autonomy = state.get("autonomy_level", "auto_resolve")
    if autonomy == "auto_resolve":
        status_details = "Resolution has been APPROVED and will be processed immediately."
    elif autonomy == "human_approval":
        status_details = (
            "Resolution has been submitted for supervisor review. "
            "You will be notified once approved (usually within 2-4 hours)."
        )
    elif autonomy == "escalate":
        status_details = (
            "This case has been escalated to our specialized team. "
            "A senior representative will contact you within 24 hours."
        )
    else:
        status_details = "Your case is being processed."
    
    # Handle blocked cases (injection detected)
    if state.get("injection_detected"):
        duration = (time.time() - start_time) * 1000
        return {
            "response_text": (
                "I'm sorry, but I wasn't able to process your message. "
                "Could you please rephrase your concern? I'm here to help "
                "with order issues, refunds, deliveries, and other support needs."
            ),
            "response_language": "en",
            "autonomy_level": "blocked",
            "status": "blocked",
            "current_node": "responder",
            "trace_events": [{
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node": "responder",
                "event_type": "node_complete",
                "data": {"blocked": True, "reason": "injection_detected", "autonomy_level": "blocked"},
                "duration_ms": round(duration, 2),
            }],
        }
    
    llm = ChatGoogleGenerativeAI(
        model=settings.fast_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.7,  # Higher temperature for natural-sounding responses
    )
    
    prompt = RESPONDER_PROMPT.format(
        response_language=response_language,
        sentiment=state.get("sentiment", "neutral"),
        customer_tier=state.get("customer_tier", "standard"),
        triage_summary=state.get("triage_summary", ""),
        resolution_type=state.get("resolution_type", "information"),
        resolution_amount=state.get("resolution_amount", 0),
        autonomy_level=autonomy,
        resolution_reasoning=state.get("resolution_reasoning", ""),
        status_details=status_details,
    )
    
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content
        if isinstance(content, list):
            response_text = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content).strip()
        else:
            response_text = str(content).strip()
        
        duration = (time.time() - start_time) * 1000
        
        trace_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node": "responder",
            "event_type": "node_complete",
            "data": {
                "response_language": response_language,
                "response_length": len(response_text),
                "autonomy_level": autonomy,
            },
            "duration_ms": round(duration, 2),
        }
        
        return {
            "response_text": response_text,
            "response_language": detected_lang,
            "current_node": "responder",
            "trace_events": [trace_event],
        }
    
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        
        # Fallback response if LLM fails
        fallback = (
            "Thank you for reaching out. We've received your concern and "
            "our team is looking into it. We'll get back to you shortly."
        )
        
        return {
            "response_text": fallback,
            "response_language": "en",
            "current_node": "responder",
            "trace_events": [{
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node": "responder",
                "event_type": "error",
                "data": {"error": str(e), "used_fallback": True},
                "duration_ms": round(duration, 2),
            }],
        }
