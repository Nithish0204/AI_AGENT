"""
Database Models & Session Management
=====================================

Uses SQLAlchemy 2.0 async with SQLite (via aiosqlite).
SQLite is perfect for a hackathon: zero setup, single file, fast enough
for our demo data (40 orders, 20 customers).

For production, swap DATABASE_URL to PostgreSQL — the code stays the same
thanks to SQLAlchemy's abstraction.
"""

import os
import json
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, Text, DateTime, ForeignKey,
    create_engine, event,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import get_settings

Base = declarative_base()


# ============================================================
# Database Models
# ============================================================

class Customer(Base):
    """A customer who can submit support cases."""
    __tablename__ = "customers"
    
    id = Column(String, primary_key=True)           # e.g., "CUST-001"
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, default="")
    tier = Column(String, default="standard")       # "vip", "premium", "standard"
    address = Column(Text, default="")
    total_orders = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    orders = relationship("Order", back_populates="customer")
    cases = relationship("Case", back_populates="customer")


class Order(Base):
    """A customer order — the core business object agents need to look up."""
    __tablename__ = "orders"
    
    id = Column(String, primary_key=True)           # e.g., "ORD-1001"
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    product_name = Column(String, nullable=False)
    product_category = Column(String, default="")
    quantity = Column(Integer, default=1)
    amount = Column(Float, nullable=False)          # Total order amount
    status = Column(String, nullable=False)         # "delivered", "shipped", "cancelled", etc.
    ordered_at = Column(DateTime, nullable=False)
    shipped_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    expected_delivery = Column(DateTime, nullable=True)
    carrier = Column(String, default="")
    tracking_number = Column(String, default="")
    shipping_address = Column(Text, default="")
    is_refunded = Column(Boolean, default=False)
    refund_amount = Column(Float, default=0.0)
    refund_date = Column(DateTime, nullable=True)
    notes = Column(Text, default="")                # Internal notes
    
    customer = relationship("Customer", back_populates="orders")


class Case(Base):
    """A customer support case — tracks the full lifecycle of a complaint."""
    __tablename__ = "cases"
    
    id = Column(String, primary_key=True)           # e.g., "CASE-001"
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    customer_message = Column(Text, nullable=False)
    detected_language = Column(String, default="en")
    status = Column(String, default="processing")   # processing, resolved, escalated, etc.
    
    # Triage results
    intents = Column(Text, default="[]")            # JSON list
    order_id = Column(String, nullable=True)
    sentiment = Column(String, default="neutral")
    urgency = Column(String, default="medium")
    triage_summary = Column(Text, default="")
    
    # Resolution
    resolution_type = Column(String, nullable=True)
    resolution_amount = Column(Float, default=0.0)
    resolution_reasoning = Column(Text, default="")
    resolution_confidence = Column(Float, default=0.0)
    risk_level = Column(String, default="low")
    autonomy_level = Column(String, nullable=True)
    
    # Response
    response_text = Column(Text, default="")
    
    # Human-in-the-loop
    human_decision = Column(String, nullable=True)
    human_notes = Column(Text, nullable=True)
    
    # Metadata
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    response_time_ms = Column(Float, default=0.0)
    trace_events = Column(Text, default="[]")       # JSON array of trace events
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))
    
    customer = relationship("Customer", back_populates="cases")


# ============================================================
# Database Session Management
# ============================================================

# Async engine for FastAPI
_async_engine = None
_async_session_factory = None

# Sync engine for seed scripts and Alembic
_sync_engine = None


def _ensure_sqlite_dir(url: str):
    """Ensure parent directory exists for SQLite database files."""
    if "sqlite" in url:
        path_part = url.split(":///")[-1] if ":///" in url else url.split("://")[-1]
        if path_part and path_part != ":memory:":
            db_dir = os.path.dirname(path_part)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)


def get_async_engine():
    """Get or create the async database engine."""
    global _async_engine
    if _async_engine is None:
        settings = get_settings()
        _ensure_sqlite_dir(settings.database_url)
        _async_engine = create_async_engine(
            settings.database_url,
            echo=False,
            # SQLite needs these for async support
            connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
        )
    return _async_engine


def get_sync_engine():
    """Get or create a sync database engine (for seed scripts)."""
    global _sync_engine
    if _sync_engine is None:
        settings = get_settings()
        # Convert async URL to sync
        sync_url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
        _ensure_sqlite_dir(sync_url)
        _sync_engine = create_engine(sync_url, echo=False)
    return _sync_engine


def get_async_session_factory():
    """Get the async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_async_engine()
        _async_session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_factory


async def get_db_session() -> AsyncSession:
    """FastAPI dependency that provides a database session."""
    factory = get_async_session_factory()
    async with factory() as session:
        yield session


async def init_db():
    """Create all tables. Called on application startup."""
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_db_sync():
    """Synchronous version for seed scripts."""
    engine = get_sync_engine()
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()
