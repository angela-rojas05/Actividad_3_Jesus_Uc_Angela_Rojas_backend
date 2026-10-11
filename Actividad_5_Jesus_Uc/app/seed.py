from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    CompanyUser,
    CompanyUserRoleModel,
    PermissionModel,
    RoleModel,
    RolePermissionModel,
)


ROLES_DATA = [
    {
        "code": "ADMINISTRADOR",
        "name": "Administrador",
        "description": "Acceso total y administración de la empresa y configuración.",
    },
    {
        "code": "CONTADOR",
        "name": "Contador",
        "description": "Gestión contable, cuentas, conceptos y transacciones.",
    },
    {
        "code": "CAPTURISTA",
        "name": "Capturista",
        "description": "Captura y consulta de transacciones y catálogos operativos.",
    },
    {
        "code": "CONSULTA",
        "name": "Consulta",
        "description": "Acceso de solo lectura a la información financiera y usuarios.",
    },
]

PERMISSIONS_DATA = [
    {
        "code": "company.users.read",
        "name": "Ver usuarios de empresa",
        "description": "Permite consultar los usuarios asociados a la empresa.",
    },
    {
        "code": "company.users.write",
        "name": "Gestionar usuarios de empresa",
        "description": "Permite asignar y modificar usuarios en la empresa.",
    },
    {
        "code": "accounts.read",
        "name": "Ver cuentas",
        "description": "Permite consultar las cuentas financieras.",
    },
    {
        "code": "accounts.write",
        "name": "Gestionar cuentas",
        "description": "Permite crear, actualizar y desactivar cuentas financieras.",
    },
    {
        "code": "concepts.read",
        "name": "Ver conceptos",
        "description": "Permite consultar los conceptos financieros.",
    },
    {
        "code": "concepts.write",
        "name": "Gestionar conceptos",
        "description": "Permite crear, actualizar y desactivar conceptos financieros.",
    },
    {
        "code": "transactions.read",
        "name": "Ver transacciones",
        "description": "Permite consultar los movimientos financieros.",
    },
    {
        "code": "transactions.write",
        "name": "Gestionar transacciones",
        "description": "Permite registrar y modificar movimientos financieros.",
    },
    {
        "code": "roles.read",
        "name": "Ver roles",
        "description": "Permite consultar los roles y permisos del sistema.",
    },
    {
        "code": "roles.write",
        "name": "Gestionar roles",
        "description": "Permite asignar y modificar roles y permisos.",
    },
]

ROLE_PERMISSIONS_MATRIX: dict[str, list[str]] = {
    "ADMINISTRADOR": [
        "company.users.read",
        "company.users.write",
        "accounts.read",
        "accounts.write",
        "concepts.read",
        "concepts.write",
        "transactions.read",
        "transactions.write",
        "roles.read",
        "roles.write",
    ],
    "CONTADOR": [
        "company.users.read",
        "accounts.read",
        "accounts.write",
        "concepts.read",
        "concepts.write",
        "transactions.read",
        "transactions.write",
        "roles.read",
    ],
    "CAPTURISTA": [
        "accounts.read",
        "concepts.read",
        "transactions.read",
        "transactions.write",
    ],
    "CONSULTA": [
        "company.users.read",
        "accounts.read",
        "concepts.read",
        "transactions.read",
    ],
}


def seed_roles(db: Session | None = None) -> None:
    if db is None:
        with SessionLocal() as session:
            seed_roles(session)
            session.commit()
        return

    count = db.scalar(select(func.count(RoleModel.id))) or 0
    if count == 0:
        for r in ROLES_DATA:
            role = RoleModel(
                code=r["code"],
                name=r["name"],
                description=r["description"],
                is_active=True,
            )
            db.add(role)
        db.flush()


def seed_permissions(db: Session | None = None) -> None:
    if db is None:
        with SessionLocal() as session:
            seed_permissions(session)
            session.commit()
        return

    count = db.scalar(select(func.count(PermissionModel.id))) or 0
    if count == 0:
        for p in PERMISSIONS_DATA:
            perm = PermissionModel(
                code=p["code"],
                name=p["name"],
                description=p["description"],
                is_active=True,
            )
            db.add(perm)
        db.flush()


def seed_role_permissions(db: Session | None = None) -> None:
    if db is None:
        with SessionLocal() as session:
            seed_role_permissions(session)
            session.commit()
        return

    all_permissions = {
        p.code: p for p in db.scalars(select(PermissionModel)).all()
    }

    for role_code, perm_codes in ROLE_PERMISSIONS_MATRIX.items():
        role = db.scalar(select(RoleModel).where(RoleModel.code == role_code))
        if not role:
            continue

        existing_rp_count = db.scalar(
            select(func.count(RolePermissionModel.id)).where(
                RolePermissionModel.role_id == role.id
            )
        ) or 0

        if existing_rp_count == 0:
            for p_code in perm_codes:
                perm = all_permissions.get(p_code)
                if perm:
                    rp = RolePermissionModel(
                        role_id=role.id,
                        permission_id=perm.id,
                        is_active=True,
                    )
                    db.add(rp)
            db.flush()


def backfill_company_user_roles(db: Session | None = None) -> None:
    if db is None:
        with SessionLocal() as session:
            backfill_company_user_roles(session)
            session.commit()
        return

    admin_role = db.scalar(
        select(RoleModel).where(RoleModel.code == "ADMINISTRADOR")
    )
    consulta_role = db.scalar(
        select(RoleModel).where(RoleModel.code == "CONSULTA")
    )

    if not admin_role or not consulta_role:
        return

    active_company_users = db.scalars(
        select(CompanyUser).where(CompanyUser.is_active == True)
    ).all()

    for cu in active_company_users:
        active_role_count = db.scalar(
            select(func.count(CompanyUserRoleModel.id)).where(
                CompanyUserRoleModel.company_user_id == cu.id,
                CompanyUserRoleModel.is_active == True,
            )
        ) or 0

        if active_role_count == 0:
            target_role = admin_role if cu.is_admin else consulta_role
            existing_cur = db.scalar(
                select(CompanyUserRoleModel).where(
                    CompanyUserRoleModel.company_user_id == cu.id,
                    CompanyUserRoleModel.role_id == target_role.id,
                )
            )
            if existing_cur:
                existing_cur.is_active = True
            else:
                new_cur = CompanyUserRoleModel(
                    company_user_id=cu.id,
                    role_id=target_role.id,
                    is_active=True,
                )
                db.add(new_cur)

    db.flush()
