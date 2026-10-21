"""Prepara los datos de demo de la Actividad 6 (repetible).

Empresa 1: Ana (ADMINISTRADOR), Luis (CONTADOR), María (CAPTURISTA),
           Pedro (CONSULTA), una cuenta y un concepto válidos.
Empresa 2: un administrador para el caso 8 (otra empresa).

Se puede ejecutar varias veces: reutiliza lo que ya existe (por correo o
nombre), vuelve a dejar a cada persona en su rol inicial (Pedro = CONSULTA)
y no duplica filas.  Escribe scripts/ids_demo.json (ignorado por Git).
"""
import json
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.financial_models import Account, AccountConcept, Concept  # noqa: E402
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
IDS_FILE = ROOT / "scripts" / "ids_demo.json"

EMPRESA_1 = "Empresa Demo Actividad 6"
EMPRESA_2 = "Empresa Dos Actividad 6"

PERSONAS = [
    # clave, nombre, correo, rol, empresa (1 o 2)
    ("ana", "Ana", "ana@actividad6.com", "ADMINISTRADOR", 1),
    ("luis", "Luis", "luis@actividad6.com", "CONTADOR", 1),
    ("maria", "María", "maria@actividad6.com", "CAPTURISTA", 1),
    ("pedro", "Pedro", "pedro@actividad6.com", "CONSULTA", 1),
    ("admin2", "Admin Dos", "admin2@actividad6.com", "ADMINISTRADOR", 2),
]


def obtener_empresa(db, nombre):
    empresa = db.scalar(select(Company).where(Company.name == nombre))
    if empresa is None:
        empresa = Company(name=nombre, is_active=True)
        db.add(empresa)
        db.flush()
    empresa.is_active = True
    return empresa


def obtener_persona(db, empresa, nombre, correo, rol_codigo, es_admin):
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
                         is_admin=es_admin, is_active=True)
        db.add(cu)
        db.flush()
    cu.is_active = True

    # Deja UN solo rol activo: el inicial de la persona.
    rol = db.scalar(select(RoleModel).where(RoleModel.code == rol_codigo))
    asignaciones = db.scalars(select(CompanyUserRoleModel).where(
        CompanyUserRoleModel.company_user_id == cu.id)).all()
    objetivo = None
    for a in asignaciones:
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


def main():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_roles(db)
        seed_permissions(db)
        seed_role_permissions(db)
        backfill_company_user_roles(db)
        db.flush()

        empresas = {1: obtener_empresa(db, EMPRESA_1),
                    2: obtener_empresa(db, EMPRESA_2)}

        datos = {}
        for clave, nombre, correo, rol, num in PERSONAS:
            user, cu = obtener_persona(
                db, empresas[num], nombre, correo, rol,
                es_admin=(rol == "ADMINISTRADOR"))
            datos[clave] = {"nombre": nombre, "correo": correo, "rol": rol,
                            "userId": user.id, "companyUserId": cu.id,
                            "companyId": empresas[num].id}

        # Cuenta y concepto válidos de la empresa 1 (y su vínculo activo)
        cuenta = db.scalar(select(Account).where(
            Account.company_id == empresas[1].id,
            Account.name == "Cuenta Demo A6"))
        if cuenta is None:
            cuenta = Account(company_id=empresas[1].id, account_type="DEBIT",
                             name="Cuenta Demo A6",
                             short_description="Cuenta de la demo")
            db.add(cuenta)
        cuenta.is_active = True

        concepto = db.scalar(select(Concept).where(
            Concept.company_id == empresas[1].id,
            Concept.concept_type == "INCOME",
            Concept.name == "Venta Demo A6"))
        if concepto is None:
            concepto = Concept(company_id=empresas[1].id,
                               concept_type="INCOME", name="Venta Demo A6",
                               short_description="Concepto de la demo")
            db.add(concepto)
        concepto.is_active = True
        db.flush()

        vinculo = db.scalar(select(AccountConcept).where(
            AccountConcept.account_id == cuenta.id,
            AccountConcept.concept_id == concepto.id))
        if vinculo is None:
            db.add(AccountConcept(account_id=cuenta.id,
                                  concept_id=concepto.id))
        else:
            vinculo.is_active = True
        db.commit()

        resultado = {
            "password": PASSWORD,
            "empresa1": {"id": empresas[1].id, "nombre": EMPRESA_1},
            "empresa2": {"id": empresas[2].id, "nombre": EMPRESA_2},
            "accountId": cuenta.id,
            "conceptId": concepto.id,
            "personas": datos,
        }

    IDS_FILE.write_text(json.dumps(resultado, indent=2, ensure_ascii=False),
                        encoding="utf-8")

    print("=" * 62)
    print(" DATOS DE DEMO - ACTIVIDAD 6")
    print("=" * 62)
    print(f" Contraseña de todos : {PASSWORD}")
    print(f" Empresa 1           : id {resultado['empresa1']['id']}")
    print(f" Empresa 2           : id {resultado['empresa2']['id']}")
    print(f" Cuenta / Concepto   : {resultado['accountId']} / "
          f"{resultado['conceptId']}")
    print("-" * 62)
    print(f" {'Persona':<10}{'Rol':<15}{'userId':<8}{'companyUserId':<15}Correo")
    for d in datos.values():
        print(f" {d['nombre']:<10}{d['rol']:<15}{d['userId']:<8}"
              f"{d['companyUserId']:<15}{d['correo']}")
    print("=" * 62)
    print(f" IDs guardados en {IDS_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
