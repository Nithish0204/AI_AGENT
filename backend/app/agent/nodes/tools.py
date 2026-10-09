"""
TOOLS Node: Executing Data Lookups and Actions
================================================

This node executes the tools identified by the planner.
Tools are pure functions that access data — they don't make decisions.

KEY CONCEPT - Tool Calling:
In an agent system, "tools" are functions the LLM can use to access
external data or perform actions. But critically, in our architecture,
the LLM doesn't call tools directly. Instead:
1. The PLANNER decides which tools are needed
2. This TOOLS node executes them in parallel where possible
3. Results are stored in state for the REASONER to use

This is safer than letting the LLM call tools ad-hoc because:
- We control WHICH tools run (planner) and WHAT data they access (this node)
- Tools like check_refund_eligibility are pure code, not LLM calls
- We can add timeouts, retries, and access control per tool
"""

import time
import asyncio
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import CaseState
from app.models.database import Order, Customer, Case, get_async_session_factory
from app.config import get_settings


# ============================================================
# Tool: Get Order Details
# ============================================================

async def get_order(order_id: str, customer_id: str) -> dict | None:
    """
    Look up an order by ID. CRITICAL: only return orders belonging
    to the verified customer_id (data isolation / access control).
    
    KEY CONCEPT - Data Isolation:
    A customer should ONLY see their own orders. If someone sends
    "Show me order ORD-9999" but that order belongs to another customer,
    we return None. This prevents data leakage attacks.
    """
    factory = get_async_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Order).where(
                Order.id == order_id,
                Order.customer_id == customer_id  # ACCESS CONTROL: must match
            )
        )
        order = result.scalar_one_or_none()
        
        if not order:
            return None
        
        return {
            "order_id": order.id,
            "customer_id": order.customer_id,
            "product_name": order.product_name,
            "product_category": order.product_category,
            "quantity": order.quantity,
            "amount": order.amount,
            "status": order.status,
            "ordered_at": order.ordered_at.isoformat() if order.ordered_at else None,
            "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
            "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
            "expected_delivery": order.expected_delivery.isoformat() if order.expected_delivery else None,
            "carrier": order.carrier,
            "tracking_number": order.tracking_number,
            "is_refunded": order.is_refunded,
            "refund_amount": order.refund_amount,
            "refund_date": order.refund_date.isoformat() if order.refund_date else None,
            "notes": order.notes,
        }


# ============================================================
# Tool: Get Customer History
# ============================================================

async def get_customer_history(customer_id: str) -> dict | None:
    """
    Get customer's profile, past orders, and refund history.
    Used by the reasoner to understand patterns (e.g., repeat complainers).
    """
    factory = get_async_session_factory()
    async with factory() as session:
        # Get customer profile
        cust_result = await session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = cust_result.scalar_one_or_none()
        if not customer:
            return None
        
        # Get all orders
        orders_result = await session.execute(
            select(Order).where(Order.customer_id == customer_id).order_by(Order.ordered_at.desc())
        )
        orders = orders_result.scalars().all()
        
        # Get past cases
        cases_result = await session.execute(
            select(Case).where(Case.customer_id == customer_id).order_by(Case.created_at.desc())
        )
        cases = cases_result.scalars().all()
        
        # Calculate refund statistics
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        refunded_orders = [o for o in orders if o.is_refunded]
        recent_refunds = [o for o in refunded_orders 
                         if o.refund_date and o.refund_date.replace(tzinfo=timezone.utc) > thirty_days_ago]
        
        return {
            "customer_id": customer.id,
            "name": customer.name,
            "tier": customer.tier,
            "total_orders": len(orders),
            "total_spent": sum(o.amount for o in orders),
            "total_refunds": len(refunded_orders),
            "total_refund_amount": sum(o.refund_amount for o in refunded_orders),
            "refunds_last_30_days": len(recent_refunds),
            "refund_amount_last_30_days": sum(o.refund_amount for o in recent_refunds),
            "past_cases_count": len(cases),
            "recent_orders": [
                {"id": o.id, "product": o.product_name, "amount": o.amount,
                 "status": o.status, "is_refunded": o.is_refunded}
                for o in orders[:5]  # Last 5 orders
            ],
        }


# ============================================================
# Tool: Check Shipment Status
# ============================================================

async def check_shipment_status(order_id: str, customer_id: str) -> dict | None:
    """
    Check carrier tracking status for an order.
    In production, this would call the carrier's API.
    Here we derive status from order data (mock).
    """
    order = await get_order(order_id, customer_id)
    if not order:
        return None
    
    now = datetime.now(timezone.utc)
    
    # Derive shipment status from order data
    if order["status"] == "delivered":
        delivered_at = datetime.fromisoformat(order["delivered_at"]) if order["delivered_at"] else None
        expected = datetime.fromisoformat(order["expected_delivery"]) if order["expected_delivery"] else None
        
        is_late = False
        days_late = 0
        if delivered_at and expected:
            # Make both timezone-aware for comparison
            if delivered_at.tzinfo is None:
                delivered_at = delivered_at.replace(tzinfo=timezone.utc)
            if expected.tzinfo is None:
                expected = expected.replace(tzinfo=timezone.utc)
            is_late = delivered_at > expected
            days_late = max(0, (delivered_at - expected).days) if is_late else 0
        
        return {
            "order_id": order_id,
            "carrier": order["carrier"],
            "tracking_number": order["tracking_number"],
            "status": "delivered",
            "delivered_at": order["delivered_at"],
            "is_late": is_late,
            "days_late": days_late,
            "expected_delivery": order["expected_delivery"],
        }
    
    elif order["status"] == "shipped":
        expected = datetime.fromisoformat(order["expected_delivery"]) if order["expected_delivery"] else None
        is_overdue = False
        days_overdue = 0
        if expected:
            if expected.tzinfo is None:
                expected = expected.replace(tzinfo=timezone.utc)
            is_overdue = now > expected
            days_overdue = max(0, (now - expected).days) if is_overdue else 0
        
        return {
            "order_id": order_id,
            "carrier": order["carrier"],
            "tracking_number": order["tracking_number"],
            "status": "in_transit",
            "shipped_at": order["shipped_at"],
            "expected_delivery": order["expected_delivery"],
            "is_overdue": is_overdue,
            "days_overdue": days_overdue,
        }
    
    else:
        return {
            "order_id": order_id,
            "status": order["status"],
            "carrier": order.get("carrier", ""),
            "tracking_number": order.get("tracking_number", ""),
            "message": f"Order is in '{order['status']}' state",
        }


# ============================================================
# Tool: Check Refund Eligibility
# ============================================================

def check_refund_eligibility(order_data: dict, customer_history: dict | None = None) -> dict:
    """
    Determine if a refund is eligible based on DETERMINISTIC business rules.
    
    KEY CONCEPT - Code-Based Decisions:
    This is intentionally NOT an LLM call. Refund eligibility is computed
    by CODE using explicit business rules. The LLM can PROPOSE a refund,
    but this function is the AUTHORITY on whether it's allowed.
    
    Why? Because:
    1. Business rules must be deterministic and auditable
    2. LLMs can be convinced to bypass rules (prompt injection)
    3. If the rules change, we change code — not hope the LLM adapts
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    reasons = []
    blockers = []
    
    if not order_data:
        return {
            "eligible": False,
            "blockers": ["Order not found"],
            "reasons": [],
            "max_refund_amount": 0.0,
        }
    
    amount = order_data.get("amount", 0)
    status = order_data.get("status", "")
    
    # Rule 1: Already refunded
    if order_data.get("is_refunded"):
        blockers.append("Order already refunded")
        return {
            "eligible": False,
            "blockers": blockers,
            "reasons": ["Previous refund of ₹{:.2f} on {}".format(
                order_data.get("refund_amount", 0),
                order_data.get("refund_date", "unknown")
            )],
            "max_refund_amount": 0.0,
        }
    
    # Rule 2: Return window (30 days from delivery)
    delivered_at = None
    if order_data.get("delivered_at"):
        delivered_at = datetime.fromisoformat(order_data["delivered_at"])
        if delivered_at.tzinfo is None:
            delivered_at = delivered_at.replace(tzinfo=timezone.utc)
        days_since_delivery = (now - delivered_at).days
        
        if days_since_delivery > 30:
            blockers.append(f"Return window expired ({days_since_delivery} days since delivery, max 30)")
        else:
            reasons.append(f"Within return window ({days_since_delivery}/30 days)")
    
    # Rule 3: Order status
    if status == "cancelled":
        reasons.append("Order was cancelled — refund applicable")
    elif status == "payment_error" or status == "payment_failed":
        reasons.append("Payment error detected — refund applicable")
    elif status in ("processing", "shipped"):
        reasons.append("Order not yet delivered — cancellation refund applicable")
    elif status == "delivered":
        reasons.append("Order delivered — return/refund window applies")
    
    # Rule 4: Fraud check
    if customer_history:
        recent_refunds = customer_history.get("refunds_last_30_days", 0)
        if recent_refunds >= settings.max_refund_claims_30_days:
            blockers.append(
                f"Fraud alert: {recent_refunds} refunds in last 30 days "
                f"(threshold: {settings.max_refund_claims_30_days})"
            )
    
    # Determine max refund amount
    max_refund = amount if not blockers else 0.0
    
    # Partial refund for late delivery (10% compensation, max ₹500)
    if status == "delivered" and order_data.get("notes", "").lower().find("late") >= 0:
        compensation = min(amount * 0.1, 500.0)
        reasons.append(f"Late delivery compensation eligible: ₹{compensation:.2f}")
    
    return {
        "eligible": len(blockers) == 0,
        "blockers": blockers,
        "reasons": reasons,
        "max_refund_amount": max_refund,
        "order_amount": amount,
    }


# ============================================================
# TOOLS NODE (orchestrates all tool calls)
# ============================================================

async def tools_node(state: CaseState) -> dict:
    """
    Execute all tools specified in the execution plan.
    Runs independent tools in PARALLEL using asyncio.gather().
    
    KEY CONCEPT - Parallel Tool Execution:
    If the planner says we need order data AND policy search AND customer history,
    we run all three AT THE SAME TIME (not sequentially). This cuts latency
    from sum(individual_latencies) to max(individual_latencies).
    """
    start_time = time.time()
    plan = state.get("execution_plan", [])
    customer_id = state.get("customer_id", "")
    order_id = state.get("order_id", "")
    
    results = {
        "order_data": state.get("order_data"),
        "customer_history": state.get("customer_history"),
        "shipment_data": state.get("shipment_data"),
        "refund_eligibility": state.get("refund_eligibility"),
        "retrieved_policies": state.get("retrieved_policies", []),
    }
    
    trace_events = []
    
    # Build list of async tasks to run in parallel
    tasks = {}
    
    if "get_order" in plan and order_id:
        tasks["get_order"] = get_order(order_id, customer_id)
    
    if "get_customer_history" in plan:
        tasks["get_customer_history"] = get_customer_history(customer_id)
    
    if "check_shipment_status" in plan and order_id:
        tasks["check_shipment_status"] = check_shipment_status(order_id, customer_id)
    
    if "search_knowledge_base" in plan:
        # Import here to avoid circular imports
        from app.knowledge.retriever import search_policies
        query = state.get("triage_summary", state.get("customer_message", ""))
        tasks["search_knowledge_base"] = asyncio.to_thread(search_policies, query)
    
    # Execute all tasks in parallel
    if tasks:
        task_names = list(tasks.keys())
        task_coroutines = list(tasks.values())
        
        try:
            task_results = await asyncio.gather(*task_coroutines, return_exceptions=True)
            
            for name, result in zip(task_names, task_results):
                tool_start = time.time()
                if isinstance(result, Exception):
                    trace_events.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "node": "tools",
                        "event_type": "tool_error",
                        "data": {"tool": name, "error": str(result)},
                    })
                else:
                    if name == "get_order":
                        results["order_data"] = result
                    elif name == "get_customer_history":
                        results["customer_history"] = result
                    elif name == "check_shipment_status":
                        results["shipment_data"] = result
                    elif name == "search_knowledge_base":
                        results["retrieved_policies"] = result if result else []
                    
                    trace_events.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "node": "tools",
                        "event_type": "tool_complete",
                        "data": {
                            "tool": name,
                            "result_summary": _summarize_tool_result(name, result),
                        },
                    })
        except Exception as e:
            trace_events.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node": "tools",
                "event_type": "error",
                "data": {"error": str(e)},
            })
    
    # Run refund eligibility check (depends on order_data, so runs AFTER)
    if "check_refund_eligibility" in plan and results.get("order_data"):
        eligibility = check_refund_eligibility(
            results["order_data"], results.get("customer_history")
        )
        results["refund_eligibility"] = eligibility
        trace_events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node": "tools",
            "event_type": "tool_complete",
            "data": {
                "tool": "check_refund_eligibility",
                "result_summary": {
                    "eligible": eligibility["eligible"],
                    "max_refund": eligibility["max_refund_amount"],
                    "blockers": eligibility["blockers"],
                },
            },
        })
    
    duration = (time.time() - start_time) * 1000
    
    trace_events.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": "tools",
        "event_type": "node_complete",
        "data": {"tools_executed": list(tasks.keys()), "total_tools": len(tasks)},
        "duration_ms": round(duration, 2),
    })
    
    return {
        **results,
        "current_node": "tools",
        "trace_events": trace_events,
    }


def _summarize_tool_result(name: str, result) -> dict:
    """Create a safe summary of tool results for the trace panel."""
    if result is None:
        return {"found": False}
    
    if name == "get_order":
        return {
            "found": True,
            "order_id": result.get("order_id"),
            "status": result.get("status"),
            "amount": result.get("amount"),
            "product": result.get("product_name"),
        }
    elif name == "get_customer_history":
        return {
            "found": True,
            "tier": result.get("tier"),
            "total_orders": result.get("total_orders"),
            "refunds_30d": result.get("refunds_last_30_days"),
        }
    elif name == "check_shipment_status":
        return {
            "found": True,
            "status": result.get("status"),
            "is_late": result.get("is_late", result.get("is_overdue", False)),
        }
    elif name == "search_knowledge_base":
        return {
            "chunks_found": len(result) if isinstance(result, list) else 0,
        }
    return {"result": "available"}
