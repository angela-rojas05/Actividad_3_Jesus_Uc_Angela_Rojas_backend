"""Prepara (o restaura) los datos de la Unidad III, Actividad 2 (repetible).

1. Restaura la demo de la Actividad 7 (preparar_demo_actividad7.py): Empresa A
   con Ana (ADMINISTRADOR), Luis, María y Pedro (CONSULTA), y sus balances.
2. Deja las cuentas de la Empresa A como en la figura 11 de la guía:
   Banco (Débito, BBVA), Caja (Efectivo) y Ahorro (Ahorro, Banorte).
3. Quita lo que se dio de alta en pruebas anteriores del dashboard
   administrativo en la Empresa A: membresías nuevas, cuentas nuevas y
   conceptos nuevos.  Así el correo, la cuenta y el concepto de la demo se
   pueden volver a capturar.  Lo que ya tenga movimientos no se borra.
4. Escribe variables/u3a2_*.json para probar la idempotencia en GraphiQL.

Uso:  python scripts/preparar_demo_u3a2.py
"""
import json
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import preparar_demo_actividad7 as demo7  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.financial_models import Account, AccountConcept, Concept, Transaction  # noqa: E402
from app.models import CompanyUser, User  # noqa: E402

SALIDA = ROOT / "variables"

# Cómo se ven las cuentas de la demo en la pantalla Cuentas (figura 11).
CUENTAS_FIGURA = {
    "Banco": {"account_type": "DEBIT", "bank_name": "BBVA", "clabe": "012180001234561234"},
    "Caja": {"account_type": "CASH", "bank_name": None, "clabe": None},
    "Ahorro": {"account_type": "SAVINGS", "bank_name": "Banorte", "clabe": "072180009876547788"},
}
CONCEPTOS_DEMO = {demo7.CONCEPTO_INGRESO, demo7.CONCEPTO_EGRESO, demo7.CONCEPTO_EXTRA}
CORREOS_DEMO = {correo for _, _, correo, _, _ in demo7.PERSONAS}


def escribir(nombre, datos):
    SALIDA.mkdir(exist_ok=True)
    ruta = SALIDA / f"{nombre}.json"
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return ruta.relative_to(ROOT)


def con_movimientos(db, columna, ids):
    if not ids:
        return set()
    return set(db.scalars(select(columna).where(columna.in_(ids)).distinct()).all())


def limpiar_empresa_a(db, empresa_id):
    quitados = {"usuarios": [], "cuentas": [], "conceptos": []}

    # Membresías dadas de alta desde el dashboard (no son de la demo).
    extras = db.scalars(
        select(CompanyUser).join(User).where(
            CompanyUser.company_id == empresa_id, User.email.not_in(CORREOS_DEMO))
    ).all()
    con_mov = con_movimientos(db, Transaction.captured_by, [cu.user_id for cu in extras])
    for cu in extras:
        user = cu.user
        otras = db.scalars(select(CompanyUser).where(
            CompanyUser.user_id == user.id, CompanyUser.id != cu.id)).all()
        quitados["usuarios"].append(user.email)
        db.delete(cu)
        if not otras and user.id not in con_mov:
            db.delete(user)
    db.flush()

    # Cuentas y conceptos nuevos, solo si no tienen movimientos.
    cuentas = db.scalars(select(Account).where(
        Account.company_id == empresa_id, Account.name.not_in(list(CUENTAS_FIGURA)))).all()
    con_mov = con_movimientos(db, Transaction.account_id, [c.id for c in cuentas])
    for cuenta in cuentas:
        if cuenta.id in con_mov:
            continue
        db.query(AccountConcept).filter(AccountConcept.account_id == cuenta.id).delete(
            synchronize_session=False)
        quitados["cuentas"].append(cuenta.name)
        db.delete(cuenta)
    db.flush()

    conceptos = db.scalars(select(Concept).where(
        Concept.company_id == empresa_id, Concept.name.not_in(CONCEPTOS_DEMO))).all()
    con_mov = con_movimientos(db, Transaction.concept_id, [c.id for c in conceptos])
    for concepto in conceptos:
        if concepto.id in con_mov:
            continue
        db.query(AccountConcept).filter(AccountConcept.concept_id == concepto.id).delete(
            synchronize_session=False)
        quitados["conceptos"].append(concepto.name)
        db.delete(concepto)
    db.flush()
    return quitados


def main():
    demo7.main()
    ids = json.loads(demo7.IDS_FILE.read_text("utf-8"))
    empresa_a = ids["empresas"]["A"]["id"]

    with SessionLocal() as db:
        quitados = limpiar_empresa_a(db, empresa_a)
        for nombre, datos in CUENTAS_FIGURA.items():
            cuenta = db.scalar(select(Account).where(
                Account.company_id == empresa_a, Account.name == nombre))
            for campo, valor in datos.items():
                setattr(cuenta, campo, valor)
        db.commit()

    # Variables de GraphiQL para la Parte 1 (idempotencia).  Egreso de 100.00
    # en Banco con el concepto "Egreso A7".  La llave 1 se manda dos veces.
    movimiento = {
        "accountId": str(ids["cuentas"]["banco"]),
        "conceptId": str(ids["conceptos"]["egresoA"]),
        "transactionType": "EXPENSE",
        "amount": "100.00",
        "transactionDate": "2026-11-18T12:00:00Z",
        "shortDescription": "Pago de renta (prueba de idempotencia)",
    }
    archivos = [
        escribir("u3a2_login_ana", {"input": {
            "email": ids["personas"]["ana"]["correo"], "password": ids["password"]}}),
        escribir("u3a2_tx_llave1", {"input": {
            **movimiento, "idempotencyKey": "9b1f6c1e-2d4a-4b7e-9f3a-u3a2-llave-1"}}),
        escribir("u3a2_tx_llave2", {"input": {
            **movimiento, "idempotencyKey": "4c7e2a90-8b1d-4f6e-a2c5-u3a2-llave-2"}}),
        escribir("u3a2_tx_llave1_otro_monto", {"input": {
            **movimiento, "amount": "250.00",
            "idempotencyKey": "9b1f6c1e-2d4a-4b7e-9f3a-u3a2-llave-1"}}),
        escribir("u3a2_company_users", {"companyId": str(empresa_a)}),
    ]

    print("-" * 66)
    print(" UNIDAD III, ACTIVIDAD 2")
    print(" Cuentas como en la figura 11: Banco (BBVA), Caja (Efectivo), Ahorro (Banorte)")
    for clave, lista in quitados.items():
        if lista:
            print(f" Quitados de pruebas anteriores ({clave}): {', '.join(lista)}")
    for ruta in archivos:
        print(f" escrito: {ruta}")
    print("-" * 66)


if __name__ == "__main__":
    main()
