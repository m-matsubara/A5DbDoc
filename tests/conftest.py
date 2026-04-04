"""Shared fixtures for tests."""

import pytest
from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.engine import Engine


@pytest.fixture(scope="session")
def sqlite_engine() -> Engine:
    engine = create_engine("sqlite:///:memory:")
    meta = MetaData()

    from sqlalchemy import Table

    customers = Table(
        "customers",
        meta,
        Column("id", Integer, primary_key=True),
        Column("name", String(120), nullable=False),
        Column("email", String(255), nullable=False),
        Column("notes", Text, nullable=True),
        UniqueConstraint("email", name="uq_customers_email"),
    )

    orders = Table(
        "orders",
        meta,
        Column("id", Integer, primary_key=True),
        Column("customer_id", Integer, ForeignKey("customers.id"), nullable=False),
        Column("status", String(32), nullable=False, server_default="pending"),
        Column("total_amount", Numeric(12, 2), nullable=False),
        Index("ix_orders_customer_id", "customer_id"),
        Index("ix_orders_status", "status"),
    )

    meta.create_all(engine)
    return engine


@pytest.fixture(scope="session")
def sqlite_url() -> str:
    return "sqlite:///:memory:"
