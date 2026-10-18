import uuid
from unittest import mock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import (
    Company,
    CompanyUser,
    CompanyUserRoleModel,
    PermissionModel,
    RoleModel,
    RolePermissionModel,
    User,
)
from app.schema import schema
from app.seed import seed_permissions, seed_role_permissions, seed_roles

S0 = ["accounts.read", "concepts.read", "transactions.read", "transactions.write"]
S1 = S0 + ["accounts.write"]

PREVIEW = """
query($input: SetRolePermissionsInput!, $actor: ID!) {
  previewRolePermissions(input: $input, actorCompanyUserId: $actor) {
    role { code }
    current { code }
    toActivate { code }
    toDeactivate { code }
    unchanged { code }
    finalCount
  }
}
"""

APPLY = """
mutation($input: SetRolePermissionsInput!, $actor: ID!) {
  setRolePermissions(input: $input, actorCompanyUserId: $actor) {
    role { code }
    activated { code }
    deactivated { code }
    unchanged { code }
    finalCount
    changed
  }
}
"""


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _ids_por_codigo(codigos):
    with SessionLocal() as db:
        filas = db.execute(
            select(PermissionModel.code, PermissionModel.id)
            .where(PermissionModel.code.in_(codigos))
        ).all()
    mapa = {c: str(i) for c, i in filas}
    assert set(mapa) == set(codigos), "faltan permisos en el catálogo"
    return [mapa[c] for c in codigos]


def _rol_id(codigo):
    with SessionLocal() as db:
        return str(db.scalar(select(RoleModel.id).where(RoleModel.code == codigo)))


def estado(codigo_rol="CAPTURISTA"):
    """Lee (id_relacion, codigo, activa) con una sesión NUEVA."""
    with SessionLocal() as db:
        filas = db.execute(
            select(RolePermissionModel.id, PermissionModel.code,
                   RolePermissionModel.is_active)
            .join(PermissionModel,
                  PermissionModel.id == RolePermissionModel.permission_id)
            .join(RoleModel, RoleModel.id == RolePermissionModel.role_id)
            .where(RoleModel.code == codigo_rol)
            .order_by(PermissionModel.code)
        ).all()
    return [(int(i), c, bool(a)) for i, c, a in filas]


def activos(codigo_rol="CAPTURISTA"):
    return sorted(c for _, c, a in estado(codigo_rol) if a)


def ejecutar(query, ana, role_id, permission_ids):
    return schema.execute_sync(
        query,
        variable_values={
            "input": {"roleId": role_id, "permissionIds": permission_ids},
            "actor": ana,
        },
    )


def aplicar_codigos(ana, codigos, rol="CAPTURISTA"):
    res = ejecutar(APPLY, ana, _rol_id(rol), _ids_por_codigo(codigos))
    assert res.errors is None, res.errors
    return res.data["setRolePermissions"]


def codigos(lista):
    return sorted(p["code"] for p in lista)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ana():
    Base.metadata.create_all(engine)
    seed_roles()
    seed_permissions()
    seed_role_permissions()

    sufijo = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        company = Company(name=f"Empresa Ana {sufijo}", is_active=True)
        db.add(company)
        db.flush()
        user = User(name=f"Ana {sufijo}", email=f"ana_{sufijo}@test.com",
                    password_hash="dummy12345", is_active=True)
        db.add(user)
        db.flush()
        cu = CompanyUser(company_id=company.id, user_id=user.id,
                         is_admin=True, is_active=True)
        db.add(cu)
        db.flush()
        admin = db.scalar(select(RoleModel).where(RoleModel.code == "ADMINISTRADOR"))
        db.add(CompanyUserRoleModel(company_user_id=cu.id, role_id=admin.id,
                                    is_active=True))
        db.commit()
        ids = (company.id, user.id, cu.id)

    yield str(ids[2])

    with SessionLocal() as db:
        db.query(CompanyUserRoleModel).filter(
            CompanyUserRoleModel.company_user_id == ids[2]).delete(
            synchronize_session=False)
        db.query(CompanyUser).filter(CompanyUser.id == ids[2]).delete(
            synchronize_session=False)
        db.query(User).filter(User.id == ids[1]).delete(synchronize_session=False)
        db.query(Company).filter(Company.id == ids[0]).delete(
            synchronize_session=False)
        db.commit()


@pytest.fixture(autouse=True)
def restaurar_capturista(ana):
    yield
    aplicar_codigos(ana, S0)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_preview_no_modifica_la_bd(ana):
    aplicar_codigos(ana, S0)
    antes = estado()

    res = ejecutar(PREVIEW, ana, _rol_id("CAPTURISTA"), _ids_por_codigo(S1))
    assert res.errors is None, res.errors
    plan = res.data["previewRolePermissions"]

    assert codigos(plan["toActivate"]) == ["accounts.write"]
    assert plan["toDeactivate"] == []
    assert len(plan["unchanged"]) == 4
    assert plan["finalCount"] == 5
    assert estado() == antes


def test_aplicar_dos_veces_es_idempotente(ana):
    aplicar_codigos(ana, S0)

    primera = aplicar_codigos(ana, S1)
    assert primera["changed"] is True
    assert codigos(primera["activated"]) == ["accounts.write"]

    segunda = aplicar_codigos(ana, S1)
    assert segunda["changed"] is False
    assert segunda["activated"] == []
    assert segunda["deactivated"] == []
    assert segunda["finalCount"] == 5
    assert activos() == sorted(S1)


def test_reactivar_conserva_id_de_relacion_y_sin_duplicados(ana):
    aplicar_codigos(ana, S0)
    aplicar_codigos(ana, S1)
    id_original = {c: i for i, c, _ in estado()}["accounts.write"]

    aplicar_codigos(ana, S0)
    despues_s0 = {c: (i, a) for i, c, a in estado()}
    assert despues_s0["accounts.write"] == (id_original, False)

    aplicar_codigos(ana, S1)
    despues_s1 = {c: (i, a) for i, c, a in estado()}
    assert despues_s1["accounts.write"] == (id_original, True)

    codigos_estado = [c for _, c, _ in estado()]
    assert len(codigos_estado) == len(set(codigos_estado))
    with SessionLocal() as db:
        parejas = db.execute(
            select(RolePermissionModel.role_id, RolePermissionModel.permission_id)
        ).all()
    assert len(parejas) == len(set(parejas))


def _caso_rol_inexistente(_):
    return "999999999", _ids_por_codigo(["accounts.read"])


def _caso_administrador(_):
    return _rol_id("ADMINISTRADOR"), _ids_por_codigo(["accounts.read"])


def _caso_permiso_inexistente(_):
    return _rol_id("CAPTURISTA"), _ids_por_codigo(["accounts.read"]) + ["999999999"]


def _caso_repetido_str(_):
    pid = _ids_por_codigo(["accounts.read"])[0]
    return _rol_id("CAPTURISTA"), [pid, pid]


def _caso_repetido_mixto(_):
    pid = _ids_por_codigo(["accounts.read"])[0]
    return _rol_id("CAPTURISTA"), [pid, int(pid)]


def _caso_no_numerico(_):
    return _rol_id("CAPTURISTA"), ["abc"]


CASOS_INVALIDOS = [
    pytest.param(_caso_rol_inexistente, id="rol_inexistente"),
    pytest.param(_caso_administrador, id="administrador"),
    pytest.param(_caso_permiso_inexistente, id="permiso_inexistente_mezclado"),
    pytest.param(_caso_repetido_str, id="repetido_3_3"),
    pytest.param(_caso_repetido_mixto, id="repetido_str_e_int"),
    pytest.param(_caso_no_numerico, id="no_numerico_abc"),
]


@pytest.mark.parametrize("operacion", [PREVIEW, APPLY], ids=["preview", "apply"])
@pytest.mark.parametrize("caso", CASOS_INVALIDOS)
def test_propuestas_invalidas_dan_error_y_no_cambian_estado(ana, operacion, caso):
    aplicar_codigos(ana, S0)
    antes = estado()
    antes_admin = estado("ADMINISTRADOR")

    role_id, permission_ids = caso(ana)
    res = ejecutar(operacion, ana, role_id, permission_ids)

    assert res.errors, "se esperaba al menos un error"
    assert estado() == antes
    assert estado("ADMINISTRADOR") == antes_admin


def test_lista_vacia_y_arranque_no_resiembran(ana):
    resultado = aplicar_codigos(ana, [])
    assert resultado["finalCount"] == 0
    assert activos() == []

    filas_antes = estado()
    assert len(filas_antes) >= 4

    seed_roles()
    seed_permissions()
    seed_role_permissions()

    assert activos() == []
    assert estado() == filas_antes


def test_e07_rollback_si_falla_antes_del_commit(ana):
    aplicar_codigos(ana, S0)
    antes = estado()

    flush_real = Session.flush
    marcas = {"flush": False}

    def flush_marcado(self, *args, **kwargs):
        resultado = flush_real(self, *args, **kwargs)
        marcas["flush"] = True
        return resultado

    def commit_fallido(self, *args, **kwargs):
        raise RuntimeError("fallo simulado antes del commit")

    with mock.patch.object(Session, "flush", flush_marcado), \
            mock.patch.object(Session, "commit", commit_fallido):
        res = ejecutar(APPLY, ana, _rol_id("CAPTURISTA"), _ids_por_codigo(S1))

    assert res.errors, "se esperaba un error por el commit simulado"
    assert marcas["flush"] is True, "el fallo debió ocurrir tras enviar los cambios"
    assert estado() == antes
