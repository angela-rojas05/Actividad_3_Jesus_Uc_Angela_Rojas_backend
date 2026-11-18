from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models import Company, User


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_account_company_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    bank_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(60), nullable=True)
    clabe: Mapped[str | None] = mapped_column(String(30), nullable=True)
    card_last_digits: Mapped[str | None] = mapped_column(String(8), nullable=True)
    short_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    long_description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    company: Mapped[Company] = relationship()


class Concept(Base):
    __tablename__ = "concepts"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "concept_type", "name", name="uq_concept_company_type_name"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    concept_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    long_description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    company: Mapped[Company] = relationship()


class AccountConcept(Base):
    __tablename__ = "account_concepts"
    __table_args__ = (
        UniqueConstraint("account_id", "concept_id", name="uq_account_concept"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    account: Mapped[Account] = relationship()
    concept: Mapped[Concept] = relationship()


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    transaction_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    captured_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    short_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    long_description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    account: Mapped[Account] = relationship()
    concept: Mapped[Concept] = relationship()
    captured_by_user: Mapped[User] = relationship()


class IdempotencyKey(Base):
    """Llave de idempotencia de una mutación (Unidad III, Actividad 2).

    La llave y el movimiento se guardan en el mismo COMMIT.  El índice único
    (empresa, operación, llave) es lo que impide un segundo movimiento con la
    misma llave, aun si llegan dos peticiones al mismo tiempo.
    """

    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "operation", "idempotency_key",
            name="uq_idempotency_company_operation_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    operation: Mapped[str] = mapped_column(String(50), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    # SHA-256 del cuerpo normalizado: detecta la misma llave con otros datos.
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Si se borra el movimiento (p. ej. al restaurar la demo) se va su llave.
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    transaction: Mapped[Transaction] = relationship()
