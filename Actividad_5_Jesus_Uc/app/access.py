from __future__ import annotations

from typing import Optional

from graphql import GraphQLError
from sqlalchemy.orm import Session

from app.models import (
    CompanyUser,
    CompanyUserRoleModel,
    PermissionModel,
    RolePermissionModel,
)


def exigir_permiso(db: Session, company_user_id: int, codigo: str) -> None:
    asignacion = db.query(CompanyUserRoleModel).filter(
        CompanyUserRoleModel.company_user_id == company_user_id,
        CompanyUserRoleModel.is_active.is_(True)).first()
    if asignacion is None:
        raise PermissionError("La membresía no tiene un rol activo")
    permitido = (db.query(RolePermissionModel).join(PermissionModel).filter(
        RolePermissionModel.role_id == asignacion.role_id,
        RolePermissionModel.is_active.is_(True),
        PermissionModel.code == codigo,
        PermissionModel.is_active.is_(True)).first())
    if permitido is None:
        raise PermissionError(f"El rol no tiene el permiso {codigo}")


def validar_acceso(
    db: Session,
    actor_company_user_id: int | str,
    codigo: str,
    target_company_id: Optional[int] = None,
) -> CompanyUser:
    actor = db.get(CompanyUser, int(actor_company_user_id))
    if actor is None:
        raise GraphQLError("La membresía del actor no existe.")

    if not actor.is_active:
        raise GraphQLError("La membresía del actor está inactiva.")

    if target_company_id is not None and actor.company_id != int(target_company_id):
        raise GraphQLError(
            "La membresía actora no pertenece a la misma empresa del recurso."
        )

    try:
        exigir_permiso(db, actor.id, codigo)
    except PermissionError as exc:
        raise GraphQLError(str(exc)) from exc

    return actor
