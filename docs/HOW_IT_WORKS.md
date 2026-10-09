# 🧠 How It Works: The AI Customer Support Resolution Agent

This document explains the architecture and operational flow of the agent in plain English — no jargon without explanation.

---

## 🎯 What Problem Does This Solve?

Traditional customer support bots are either:
1. **Dumb Decision Trees**: Rigid keyword responders that can't understand context or nuance.
2. **Naive LLM Wrappers**: A prompt connected directly to GPT/Claude that hallucinates policies, grants arbitrary ₹50,000 refunds, and falls for prompt injection attacks.

Our agent introduces a **Safe, Deterministic, and Auditable Agent Architecture** using **LangGraph**. It combines:
- Real-time deep semantic reasoning
- Grounded policy retrieval (RAG)
- Automated tool execution (Order & Shipment lookups)
- **Zero-Trust Guardrails**: Pure deterministic Python code that gates every critical action.

---

## 🔄 The 10-Node Agent Loop

Instead of a single LLM call, every customer interaction passes through a structured 10-node directed graph:

```
[Customer Message] 
       │
       ▼
 1. INTAKE ───────────► (Prompt Injection Detected?) ──► [BLOCKED & REFUSED]
       │
       ▼
 2. TRIAGE ───────────► (Missing Order ID / Info?) ───► [ASK CUSTOMER FOR INFO]
       │
       ▼
 3. PLANNER (Fast-path vs Full Investigation)
       │
       ▼
 4. TOOLS (Parallel execution: Order lookup, Shipment tracking, Policy search)
       │
       ▼
 5. REASONER (Synthesizes facts, calculates refund/action, assigns confidence)
       │
       ▼
 6. CRITIC (Fact-checking loop: verifies claims against retrieved policies)
       │  (Fails? Retry loop back to Reasoner)
       ▼
 7. GUARDRAIL GATE (Pure Python code: checks limits, fraud, keywords)
       │
   ┌───┴───────────────────────────────┐
   ▼                                   ▼
 [AUTO-RESOLVE]             [HUMAN APPROVAL NEEDED]
 (Amount ≤ ₹2K, Conf ≥ 85%)    (Amount ₹2K-₹10K, or Medium Conf)
   │                                   │
   └───────────────┬───────────────────┘
                   ▼
 8. RESPONDER (Drafts empathetic reply in Telugu, Hindi, or English)
                   │
                   ▼
 9. LOGGER (Persists full trace events, latency, token costs to SQLite)
```

---

## 🛡️ Core Concepts Explained

### 1. The Agent Graph (LangGraph)
An agent loop isn't just an infinite while-loop. In LangGraph:
- **State**: A structured object (`CaseState`) that holds conversation context, customer facts, retrieved evidence, confidence scores, and event traces.
- **Nodes**: Specialized functions that take the state, perform one job (e.g., triage intent, execute tools), and return state updates.
- **Edges**: Conditional pathways that decide the next step (e.g., if prompt injection is caught, divert immediately to `blocked_response`).

### 2. Multi-Stage RAG (Hybrid Search + Reranking)
Retrieval-Augmented Generation (RAG) gives the LLM access to corporate policy documents. Most implementations do naive vector search, which often misses exact policy thresholds or numbers. We use a **3-stage hybrid retrieval pipeline**:
1. **BM25 Keyword Search**: Catches exact terms like `"60 days"`, `"ORD-1007"`, or `"fragile"`.
2. **Dense Vector Search**: Catches semantic meanings (e.g., `"item smashed"` matches `"damaged item"`).
3. **Reciprocal Rank Fusion (RRF)**: Combines the ranked lists mathematically.
4. **Cross-Encoder Reranker**: Scores query-document pairs together to find the most relevant policy snippet.

### 3. Tool Calling & Data Isolation
The agent connects to backend services (Order Database, Shipping Courier API, Customer History).
- **Access Control / Isolation**: If customer `CUST-001` asks about order `ORD-9999` belonging to another customer, the tool refuses to disclose it.
- **Deterministic Tools**: Complex calculations like `check_refund_eligibility` are implemented in pure code using date math — eliminating LLM hallucination on refund deadlines.

### 4. Zero-Trust Guardrails (Code > Prompts)
Never rely on an LLM to police itself. Our **Guardrail Gate** enforces hard thresholds in Python:
- **Confidence < 0.85 OR Amount > ₹2,000**: Requires human supervisor review.
- **Amount > ₹10,000 OR Legal Keywords ("lawyer", "consumer court")**: Mandatory human escalation.
- **Fraud Flags**: 3+ recent refund requests automatically trigger fraud review.

### 5. Human-in-the-Loop (HITL)
When the guardrail flags a high-value or ambiguous case:
1. The agent pauses execution in the state `awaiting_approval`.
2. The case appears instantly in the **Supervisor Dashboard**.
3. The supervisor sees the full reasoning trace, citations, and suggested response.
4. The supervisor can **Approve**, **Edit** the payout amount or message, or **Reject/Escalate**.

### 6. Multilingual Intelligence
The agent natively handles **Telugu**, **Hindi**, and **English**:
- Intake automatically detects the language code (`te`, `hi`, `en`).
- The internal reasoning and tool calls execute in English for maximum precision.
- The responder produces a culturally nuanced, polite response in the customer's native language.
