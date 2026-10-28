"""Prepara (o restaura) los datos de la Actividad 7 (repetible).

Empresa A (referencia): cuentas Banco, Caja y Ahorro con los 6 movimientos de
la guía, todos a las 12:00:00Z.  Es el conjunto que se consulta del 26 al 30
de octubre de 2026 y debe dar la tabla de referencia.
Empresa B (laboratorio): "Cuenta Prueba B", vacía, para los casos que
agregan movimientos (B04, B05, B06, B15) y para el caso B12 (cuenta ajena).
Empresa C: sin cuentas (B03).

Ejecutarlo de nuevo RESTAURA todo: borra los movimientos de las cuentas de
las empresas A y B, los vuelve a crear (solo A), reactiva cuentas y deja los
vínculos cuenta-concepto como al inicio.  Escribe scripts/ids_demo_a7.json
(ignorado por Git).

Uso:  python scripts/preparar_demo_actividad7.py
"""
import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.financial_models import (  # noqa: E402
    Account,
    AccountConcept,
    Concept,
    Transaction,
)
from app.models import (  # noqa: E402
    Company,
    CompanyUser,
    CompanyUserRoleModel,
    RoleModel,
    User,
)
from app.security import hash_password  # noqa: E402
from app.seed import (  # noqa: E402
    backfill_company_user_roles,
    seed_permissions,
    seed_role_permissions,
    seed_roles,
)

PASSWORD = "Secreto123!"
IDS_FILE = ROOT / "scripts" / "ids_demo_a7.json"

EMPRESAS = {
    "A": "Empresa Balances A7",
    "B": "Empresa Laboratorio A7",
    "C": "Empresa Sin Cuentas A7",
}

PERSONAS = [
    # clave, nombre, correo, rol, empresa
    ("ana", "Ana", "ana@actividad7.com", "ADMINISTRADOR", "A"),
    ("luis", "Luis", "luis@actividad7.com", "CONTADOR", "A"),
    ("maria", "María", "maria@actividad7.com", "CAPTURISTA", "A"),
    ("pedro", "Pedro", "pedro@actividad7.com", "CONSULTA", "A"),
    ("adminb", "Admin B", "adminb@actividad7.com", "ADMINISTRADOR", "B"),
    ("adminc", "Admin C", "adminc@actividad7.com", "ADMINISTRADOR", "C"),
]

# Datos de la guía (Parte 1).  Todos a las 12:00:00Z.
MOVIMIENTOS = [
    # cuenta, fecha, tipo, importe, descripción
    ("Banco", datetime(2026, 10, 25, 12), "INCOME", "1000.00", "Ingreso de apertura anterior al período"),
    ("Banco", datetime(2026, 10, 26, 12), "INCOME", "3000.00", "Cobro de servicios"),
    ("Banco", datetime(2026, 10, 27, 12), "EXPENSE", "1200.00", "Pago de renta"),
    ("Banco", datetime(2026, 10, 28, 12), "EXPENSE", "1000.00", "Compra de materiales"),
    ("Caja", datetime(2026, 10, 26, 12), "INCOME", "500.00", "Venta de contado"),
    ("Caja", datetime(2026, 10, 29, 12), "EXPENSE", "700.00", "Pago de insumos"),
]

CUENTAS_A = ["Banco", "Caja", "Ahorro"]
CUENTA_B = "Cuenta Prueba B"
CONCEPTO_INGRESO = "Ingreso A7"
CONCEPTO_EGRESO = "Egreso A7"
CONCEPTO_EXTRA = "Ingreso Extra A7"  # sin vínculo: se usa en B09


def obtener_empresa(db, nombre):
    empresa = db.scalar(select(Company).where(Company.name == nombre))
    if empresa is None:
        empresa = Company(name=nombre, is_active=True)
        db.add(empresa)
        db.flush()
    empresa.is_active = True
    return empresa


def obtener_persona(db, empresa, nombre, correo, rol_codigo):
    user = db.scalar(select(User).where(User.email == correo))
    if user is None:
        user = User(name=nombre, email=correo,
                    password_hash=hash_password(PASSWORD), is_active=True)
        db.add(user)
        db.flush()
    else:
        user.name = nombre
        user.password_hash = hash_password(PASSWORD)
        user.is_active = True

    cu = db.scalar(select(CompanyUser).where(
        CompanyUser.company_id == empresa.id,
        CompanyUser.user_id == user.id))
    if cu is None:
        cu = CompanyUser(company_id=empresa.id, user_id=user.id,
                         is_admin=(rol_codigo == "ADMINISTRADOR"),
                         is_active=True)
        db.add(cu)
        db.flush()
    cu.is_active = True

    # Deja UN solo rol activo: el inicial de la persona.
    rol = db.scalar(select(RoleModel).where(RoleModel.code == rol_codigo))
    objetivo = None
    for a in db.scalars(select(CompanyUserRoleModel).where(
            CompanyUserRoleModel.company_user_id == cu.id)).all():
        if a.role_id == rol.id:
            objetivo = a
            a.is_active = True
        else:
            a.is_active = False
    if objetivo is None:
        db.add(CompanyUserRoleModel(company_user_id=cu.id, role_id=rol.id,
                                    is_active=True))
    db.flush()
    return user, cu


def obtener_cuenta(db, empresa, nombre):
    cuenta = db.scalar(select(Account).where(
        Account.company_id == empresa.id, Account.name == nombre))
    if cuenta is None:
        cuenta = Account(company_id=empresa.id, account_type="DEBIT",
                         name=nombre)
        db.add(cuenta)
    cuenta.is_active = True
    db.flush()
    return cuenta


def obtener_concepto(db, empresa, tipo, nombre):
    concepto = db.scalar(select(Concept).where(
        Concept.company_id == empresa.id,
        Concept.concept_type == tipo, Concept.name == nombre))
    if concepto is None:
        concepto = Concept(company_id=empresa.id, concept_type=tipo,
                           name=nombre)
        db.add(concepto)
    concepto.is_active = True
    db.flush()
    return concepto


def vincular(db, cuenta, concepto, activo=True):
    vinculo = db.scalar(select(AccountConcept).where(
        AccountConcept.account_id == cuenta.id,
        AccountConcept.concept_id == concepto.id))
    if vinculo is None:
        db.add(AccountConcept(account_id=cuenta.id, concept_id=concepto.id,
                              is_active=activo))
    else:
        vinculo.is_active = activo
    db.flush()


def main():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_roles(db)
        seed_permissions(db)
        seed_role_permissions(db)
        backfill_company_user_roles(db)
        db.flush()

        empresas = {k: obtener_empresa(db, n) for k, n in EMPRESAS.items()}

        personas = {}
        for clave, nombre, correo, rol, emp in PERSONAS:
            user, cu = obtener_persona(db, empresas[emp], nombre, correo, rol)
            personas[clave] = {"nombre": nombre, "correo": correo, "rol": rol,
                               "userId": user.id, "companyUserId": cu.id,
                               "companyId": empresas[emp].id}

        # Empresa A: tres cuentas y conceptos de ingreso/egreso en Banco y Caja.
        ingreso_a = obtener_concepto(db, empresas["A"], "INCOME", CONCEPTO_INGRESO)
        egreso_a = obtener_concepto(db, empresas["A"], "EXPENSE", CONCEPTO_EGRESO)
        extra_a = obtener_concepto(db, empresas["A"], "INCOME", CONCEPTO_EXTRA)
        cuentas_a = {n: obtener_cuenta(db, empresas["A"], n) for n in CUENTAS_A}
        for nombre in ("Banco", "Caja"):
            vincular(db, cuentas_a[nombre], ingreso_a)
            vincular(db, cuentas_a[nombre], egreso_a)
        # Ahorro no necesita conceptos (no tiene movimientos).  El concepto
        # extra queda sin vincular para el caso B09; si una prueba anterior
        # lo vinculó, se quita.
        db.query(AccountConcept).filter(
            AccountConcept.concept_id == extra_a.id).delete(
            synchronize_session=False)

        # Empresa B: una cuenta vacía con ambos conceptos.
        ingreso_b = obtener_concepto(db, empresas["B"], "INCOME", CONCEPTO_INGRESO)
        egreso_b = obtener_concepto(db, empresas["B"], "EXPENSE", CONCEPTO_EGRESO)
        cuenta_b = obtener_cuenta(db, empresas["B"], CUENTA_B)
        vincular(db, cuenta_b, ingreso_b)
        vincular(db, cuenta_b, egreso_b)

        # Restaurar: borrar todos los movimientos y recrear los de la guía.
        ids_cuentas = [c.id for c in cuentas_a.values()] + [cuenta_b.id]
        db.query(Transaction).filter(
            Transaction.account_id.in_(ids_cuentas)).delete(
            synchronize_session=False)
        capturista = personas["ana"]["userId"]
        for cuenta, fecha, tipo, importe, descripcion in MOVIMIENTOS:
            db.add(Transaction(
                account_id=cuentas_a[cuenta].id,
                concept_id=(ingreso_a if tipo == "INCOME" else egreso_a).id,
                transaction_type=tipo, amount=Decimal(importe),
                transaction_date=fecha, captured_by=capturista,
                short_description=descripcion))
        db.commit()

        resultado = {
            "password": PASSWORD,
            "empresas": {k: {"id": e.id, "nombre": e.name}
                         for k, e in empresas.items()},
            "cuentas": {
                "banco": cuentas_a["Banco"].id,
                "caja": cuentas_a["Caja"].id,
                "ahorro": cuentas_a["Ahorro"].id,
                "pruebaB": cuenta_b.id,
            },
            "conceptos": {
                "ingresoA": ingreso_a.id, "egresoA": egreso_a.id,
                "extraA": extra_a.id,
                "ingresoB": ingreso_b.id, "egresoB": egreso_b.id,
            },
            "personas": personas,
        }

    IDS_FILE.write_text(json.dumps(resultado, indent=2, ensure_ascii=False),
                        encoding="utf-8")

    print("=" * 66)
    print(" DATOS DE DEMO - ACTIVIDAD 7 (restaurados)")
    print("=" * 66)
    print(f" Contraseña de todos : {PASSWORD}")
    for k, e in resultado["empresas"].items():
        print(f" Empresa {k}           : id {e['id']}  ({e['nombre']})")
    print(f" Cuentas             : {resultado['cuentas']}")
    print("-" * 66)
    print(f" {'Persona':<10}{'Rol':<15}{'Empresa':<9}Correo")
    for d in personas.values():
        print(f" {d['nombre']:<10}{d['rol']:<15}{d['companyId']:<9}{d['correo']}")
    print("=" * 66)
    print(f" IDs guardados en {IDS_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
