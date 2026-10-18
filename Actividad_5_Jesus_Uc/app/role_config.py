from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import strawberry
from graphql import GraphQLError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PermissionModel, RoleModel, RolePermissionModel

ROL_PROTEGIDO = "ADMINISTRADOR"


@strawberry.enum(name="PermissionResource")
class PermissionResource(Enum):
    COMPANY_USERS = "COMPANY_USERS"
    ACCOUNTS = "ACCOUNTS"
    CONCEPTS = "CONCEPTS"
    TRANSACTIONS = "TRANSACTIONS"
    ROLES = "ROLES"


PREFIJO_POR_RECURSO = {
    PermissionResource.COMPANY_USERS: "company.users.",
    PermissionResource.ACCOUNTS: "accounts.",
    PermissionResource.CONCEPTS: "concepts.",
    PermissionResource.TRANSACTIONS: "transactions.",
    PermissionResource.ROLES: "roles.",
}


@strawberry.input(name="SetRolePermissionsInput")
class SetRolePermissionsInput:
    role_id: strawberry.ID
    permission_ids: list[strawberry.ID]


@dataclass
class PlanPermisos:
    role: RoleModel
    current: list[PermissionModel]
    to_activate: list[PermissionModel]
    to_deactivate: list[PermissionModel]
    unchanged: list[PermissionModel]
    final_count: int
    relaciones: dict[int, RolePermissionModel]

    @property
    def changed(self) -> bool:
        return bool(self.to_activate or self.to_deactivate)


def listar_catalogo(db: Session, resource):
    stmt = (select(PermissionModel)
            .where(PermissionModel.is_active.is_(True))
            .order_by(PermissionModel.code))
    if resource is not None:
        stmt = stmt.where(PermissionModel.code.startswith(
            PREFIJO_POR_RECURSO[resource], autoescape=True))
    return list(db.scalars(stmt).all())


def _parse_id(valor, etiqueta: str) -> int:
    texto = str(valor).strip()
    if not (texto.isascii() and texto.isdigit()) or int(texto) <= 0:
        raise GraphQLError(f"El id de {etiqueta} '{valor}' no es válido.")
    return int(texto)


def validar_propuesta(db: Session, role_id_raw, permission_ids_raw):
    role_id = _parse_id(role_id_raw, "rol")
    role = db.get(RoleModel, role_id)
    if role is None:
        raise GraphQLError("El rol no existe.")
    if not role.is_active:
        raise GraphQLError("El rol está inactivo.")
    if role.code == ROL_PROTEGIDO:
        raise GraphQLError(
            "No se permite configurar el rol ADMINISTRADOR con esta operación.")
    ids = [_parse_id(v, "permiso") for v in permission_ids_raw]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    if repetidos:
        raise GraphQLError(
            "IDs de permiso repetidos: " + ", ".join(str(i) for i in repetidos) + ".")
    permisos = (list(db.scalars(select(PermissionModel)
                .where(PermissionModel.id.in_(ids))).all()) if ids else [])
    faltantes = sorted(set(ids) - {p.id for p in permisos})
    if faltantes:
        raise GraphQLError(
            "Permisos inexistentes: " + ", ".join(str(i) for i in faltantes) + ".")
    inactivos = sorted(p.code for p in permisos if not p.is_active)
    if inactivos:
        raise GraphQLError("Permisos inactivos: " + ", ".join(inactivos) + ".")
    return role, permisos


def calcular_plan(db: Session, role: RoleModel, deseados) -> PlanPermisos:
    relaciones = {rp.permission_id: rp for rp in db.scalars(
        select(RolePermissionModel).where(RolePermissionModel.role_id == role.id)).all()}
    actuales = list(db.scalars(
        select(PermissionModel)
        .join(RolePermissionModel, RolePermissionModel.permission_id == PermissionModel.id)
        .where(RolePermissionModel.role_id == role.id,
               RolePermissionModel.is_active.is_(True))
        .order_by(PermissionModel.code)).all())
    ids_actuales = {p.id for p in actuales}
    ids_deseados = {p.id for p in deseados}
    por_codigo = lambda lista: sorted(lista, key=lambda p: p.code)
    return PlanPermisos(
        role=role, current=actuales,
        to_activate=por_codigo([p for p in deseados if p.id not in ids_actuales]),
        to_deactivate=por_codigo([p for p in actuales if p.id not in ids_deseados]),
        unchanged=por_codigo([p for p in deseados if p.id in ids_actuales]),
        final_count=len(deseados), relaciones=relaciones)


def aplicar_plan(db: Session, plan: PlanPermisos) -> None:
    """Modifica relaciones en la sesión y hace flush. NO hace commit."""
    for permiso in plan.to_activate:
        rel = plan.relaciones.get(permiso.id)
        if rel is not None:
            rel.is_active = True      # reactiva con el mismo id de relación
        else:
            db.add(RolePermissionModel(role_id=plan.role.id,
                                       permission_id=permiso.id, is_active=True))
    for permiso in plan.to_deactivate:
        plan.relaciones[permiso.id].is_active = False   # desactiva, no borra
    db.flush()
