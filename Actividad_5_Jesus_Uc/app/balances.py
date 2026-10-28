"""Cálculo de balances por cuenta y general (Actividad 7).

Los balances no se guardan: se calculan en cada consulta a partir de los
movimientos. Todo el cálculo se hace en MySQL con una sola consulta agregada
(SUM + CASE) y los importes viajan como Decimal, nunca como float.

Periodo (todas las fechas en UTC, días completos):
    saldo inicial = movimientos con transaction_date <  inicio
    periodo       = movimientos con transaction_date >= inicio AND < fin
donde inicio es la medianoche de fromDate y fin la medianoche del día
siguiente a toDate (excluida). Se usa transaction_date, nunca captured_at.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Optional

from graphql import GraphQLError
from sqlalchemy import Numeric, and_, case, func, select
from sqlalchemy.orm import Session

from app.financial_models import Account, Transaction

MONEDA = "MXN"
CERO = Decimal("0.00")
CENTAVO = Decimal("0.01")


@dataclass
class BalanceCuenta:
    account_id: int
    account_name: str
    is_active: bool
    opening_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    profit: Decimal
    closing_balance: Decimal
    is_in_red: bool


def limites_periodo(from_date: date, to_date: date) -> tuple[datetime, datetime]:
    """Devuelve (inicio incluido, fin excluido) en UTC para dos fechas."""
    if from_date > to_date:
        raise GraphQLError("fromDate no puede ser posterior a toDate.")
    try:
        siguiente = to_date + timedelta(days=1)
    except OverflowError as exc:
        raise GraphQLError("La fecha toDate no es válida.") from exc
    return (
        datetime.combine(from_date, time.min),
        datetime.combine(siguiente, time.min),
    )


def _dinero(valor) -> Decimal:
    """Convierte lo que devuelve MySQL a Decimal con dos decimales."""
    if valor is None:
        return CERO
    return Decimal(valor).quantize(CENTAVO)


def calcular_balances(
    db: Session,
    company_id: int,
    from_date: date,
    to_date: date,
    account_id: Optional[int] = None,
) -> list[BalanceCuenta]:
    """Balance de cada cuenta de la empresa (o solo de `account_id`).

    Parte de las cuentas y une los movimientos con LEFT JOIN: las cuentas sin
    movimientos salen con ceros. Los filtros del movimiento (activo y fecha
    anterior al fin del periodo) van en el ON y no en el WHERE para no
    descartar esas cuentas. Incluye cuentas desactivadas.
    """
    inicio, fin = limites_periodo(from_date, to_date)

    es_ingreso = Transaction.transaction_type == "INCOME"
    es_egreso = Transaction.transaction_type == "EXPENSE"
    anterior = Transaction.transaction_date < inicio
    en_periodo = and_(
        Transaction.transaction_date >= inicio,
        Transaction.transaction_date < fin,
    )

    def suma(condicion):
        return func.coalesce(
            func.sum(case((condicion, Transaction.amount), else_=0)), 0
        ).cast(Numeric(20, 2))

    stmt = (
        select(
            Account.id,
            Account.name,
            Account.is_active,
            suma(and_(anterior, es_ingreso)),
            suma(and_(anterior, es_egreso)),
            suma(and_(en_periodo, es_ingreso)),
            suma(and_(en_periodo, es_egreso)),
        )
        .select_from(Account)
        .outerjoin(
            Transaction,
            and_(
                Transaction.account_id == Account.id,
                Transaction.is_active.is_(True),
                Transaction.transaction_date < fin,
            ),
        )
        .where(Account.company_id == company_id)
        .group_by(Account.id, Account.name, Account.is_active)
        .order_by(Account.id)
    )
    if account_id is not None:
        stmt = stmt.where(Account.id == account_id)

    resultado = []
    for id_, nombre, activa, ing_prev, egr_prev, ingresos, egresos in db.execute(stmt):
        apertura = _dinero(ing_prev) - _dinero(egr_prev)
        ingresos = _dinero(ingresos)
        egresos = _dinero(egresos)
        profit = ingresos - egresos
        cierre = apertura + profit
        resultado.append(
            BalanceCuenta(
                account_id=id_,
                account_name=nombre,
                is_active=bool(activa),
                opening_balance=apertura,
                total_income=ingresos,
                total_expense=egresos,
                profit=profit,
                closing_balance=cierre,
                is_in_red=cierre < 0,
            )
        )
    return resultado
