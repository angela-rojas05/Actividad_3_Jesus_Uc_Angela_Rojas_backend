from __future__ import annotations

from typing import Optional

import jwt
from graphql import GraphQLError
from sqlalchemy.orm import Session

from app.models import (
    CompanyUser,
    CompanyUserRoleModel,
    PermissionModel,
    RolePermissionModel,
)
from app.security import ALGORITHM, JWT_SECRET


def leer_actor(db: Session, info) -> int:
    """Devuelve el company_user_id del actor a partir del token Bearer.

    El token solo identifica (companyUserId, companyId); el rol y los
    permisos se consultan en la BD en cada petición.
    """
    context = info.context
    request = context.get("request") if context is not None else None
    headers = getattr(request, "headers", None)
    authorization = headers.get("authorization", "") if headers is not None else ""
    if not authorization.startswith("Bearer "):
        raise GraphQLError("Falta el token")

    token = authorization[len("Bearer "):].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise GraphQLError("El token no es válido") from exc

    company_user_id = payload.get("companyUserId")
    company_id = payload.get("companyId")
    if not isinstance(company_user_id, int) or not isinstance(company_id, int):
        raise GraphQLError("El token no es válido")

    actor = db.get(CompanyUser, company_user_id)
    if actor is None or not actor.is_active:
        raise GraphQLError("La membresía del token no existe o está inactiva")
    if actor.company_id != company_id:
        raise GraphQLError("El token no es válido")

    return actor.id


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
    actor_id: int | str,
    codigo: str,
    target_company_id: Optional[int] = None,
) -> CompanyUser:
    actor = db.get(CompanyUser, int(actor_id))
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
