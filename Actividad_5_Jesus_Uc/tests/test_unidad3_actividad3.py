"""Unidad III, Actividad 3 - Matriz de roles y permisos.

Lo que la pantalla Roles y permisos y la columna Rol de Usuarios leen y
escriben: roles, permissions, rolePermissions, previewRolePermissions,
setRolePermissions y assignRole, todo con el token en Authorization.

Cada corrida crea sus propias empresas y personas (sufijo aleatorio) y las
borra al terminar.  La matriz es un catálogo compartido: la prueba que cambia
la columna CAPTURISTA la deja como estaba.
"""
import uuid

import pytest
from sqlalchemy import func, select

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
from app.security import hash_password
from app.seed import seed_permissions, seed_role_permissions, seed_roles

PASSWORD = "Secreto123!"

LOGIN = "mutation($input: LoginInput!) { login(input: $input) { token } }"
MATRIZ = """
query { roles(activeOnly: true) { id code name }
        permissions(activeOnly: true) { id code name } }
"""
LISTA_DEL_ROL = """
query($roleId: ID!) { rolePermissions(roleId: $roleId) { isActive permission { id code } } }
"""
VISTA_PREVIA = """
query($input: SetRolePermissionsInput!) {
  previewRolePermissions(input: $input) {
    toActivate { code } toDeactivate { code } unchanged { code } finalCount
  }
}
"""
GUARDAR = """
mutation($input: SetRolePermissionsInput!) {
  setRolePermissions(input: $input) {
    activated { code } deactivated { code } unchanged { code } finalCount changed
  }
}
"""
ASIGNAR = """
mutation($input: AssignRoleInput!) {
  assignRole(input: $input) { isActive role { code name } }
}
"""
MY_ACCESS = "query { myAccess { isAdmin role { code } permissions } }"


class FakeRequest:
    def __init__(self, token=None):
        self.headers = {}
        if token is not None:
            self.headers["authorization"] = f"Bearer {token}"


def ejecutar(query, variables=None, token=None):
    return schema.execute_sync(
        query, variable_values=variables or {}, context_value={"request": FakeRequest(token)}
    )


def token_de(correo):
    res = ejecutar(LOGIN, {"input": {"email": correo, "password": PASSWORD}})
    assert res.errors is None, res.errors
    return res.data["login"]["token"]


def error_de(res):
    assert res.errors, "se esperaba un error"
    return res.errors[0].message


def ids_activos(role_id):
    with SessionLocal() as db:
        return sorted(db.scalars(select(RolePermissionModel.permission_id).where(
            RolePermissionModel.role_id == role_id,
            RolePermissionModel.is_active.is_(True))).all())


@pytest.fixture(scope="module")
def datos():
    Base.metadata.create_all(engine)
    seed_roles()
    seed_permissions()
    seed_role_permissions()

    suf = uuid.uuid4().hex[:8]
    ids = {"suf": suf}
    with SessionLocal() as db:
        ids["roles"] = {r.code: r.id for r in db.scalars(select(RoleModel)).all()}
        ids["permisos"] = {p.code: p.id for p in db.scalars(select(PermissionModel)).all()}
        empresa = Company(name=f"Empresa U3A3 {suf}", is_active=True)
        db.add(empresa)
        db.flush()
        ids["empresa"] = empresa.id

        for clave, rol in (("ana", "ADMINISTRADOR"), ("luis", "CONTADOR"),
                           ("maria", "CAPTURISTA"), ("jose", "CAPTURISTA"),
                           ("pedro", "CONSULTA")):
            correo = f"{clave}_{suf}@u3a3.com"
            user = User(name=clave.capitalize(), email=correo,
                        password_hash=hash_password(PASSWORD), is_active=True)
            db.add(user)
            db.flush()
            cu = CompanyUser(company_id=empresa.id, user_id=user.id,
                             is_admin=(rol == "ADMINISTRADOR"), is_active=True)
            db.add(cu)
            db.flush()
            db.add(CompanyUserRoleModel(company_user_id=cu.id,
                                        role_id=ids["roles"][rol], is_active=True))
            ids[clave] = {"correo": correo, "cu": cu.id}
        db.commit()

    yield ids

    with SessionLocal() as db:
        db.query(Company).filter(Company.id == ids["empresa"]).delete(synchronize_session=False)
        db.query(User).filter(User.email.like(f"%{suf}@u3a3.com")).delete(
            synchronize_session=False)
        db.commit()


@pytest.fixture
def capturista_restaurado(datos):
    """Guarda la columna CAPTURISTA y la deja igual al terminar la prueba."""
    rol = datos["roles"]["CAPTURISTA"]
    antes = ids_activos(rol)
    yield rol, antes
    token = token_de(datos["ana"]["correo"])
    res = ejecutar(GUARDAR, {"input": {"roleId": str(rol),
                                       "permissionIds": [str(i) for i in antes]}}, token)
    assert res.errors is None, res.errors


# ---------------------------------------------------------------------------
# Lectura de la matriz
# ---------------------------------------------------------------------------

def test_la_matriz_se_lee_con_el_token(datos):
    token = token_de(datos["luis"]["correo"])  # CONTADOR: roles.read
    res = ejecutar(MATRIZ, token=token)
    assert res.errors is None, res.errors
    codigos = {r["code"] for r in res.data["roles"]}
    assert {"ADMINISTRADOR", "CONTADOR", "CAPTURISTA", "CONSULTA"} <= codigos
    assert len(res.data["permissions"]) >= 10

    for rol in res.data["roles"]:
        lista = ejecutar(LISTA_DEL_ROL, {"roleId": rol["id"]}, token)
        assert lista.errors is None, lista.errors
        assert all(r["isActive"] for r in lista.data["rolePermissions"])


def test_sin_token_no_hay_matriz():
    assert error_de(ejecutar(MATRIZ)) == "Falta el token"


@pytest.mark.parametrize("clave", ["maria", "pedro"])
def test_sin_roles_read_el_api_rechaza_la_matriz(datos, clave):
    token = token_de(datos[clave]["correo"])
    assert "roles.read" in error_de(ejecutar(MATRIZ, token=token))
    assert "roles.read" in error_de(
        ejecutar(LISTA_DEL_ROL, {"roleId": str(datos["roles"]["CAPTURISTA"])}, token))


def test_con_roles_read_y_sin_roles_write_no_se_guarda(datos):
    token = token_de(datos["luis"]["correo"])
    entrada = {"input": {"roleId": str(datos["roles"]["CONSULTA"]), "permissionIds": []}}
    # La vista previa solo lee: el contador la puede pedir.
    assert ejecutar(VISTA_PREVIA, entrada, token).errors is None
    assert "roles.write" in error_de(ejecutar(GUARDAR, entrada, token))
    asignar = {"input": {"companyUserId": str(datos["pedro"]["cu"]),
                         "roleId": str(datos["roles"]["CAPTURISTA"])}}
    assert "roles.write" in error_de(ejecutar(ASIGNAR, asignar, token))


def test_la_columna_administrador_no_se_envia(datos):
    token = token_de(datos["ana"]["correo"])
    entrada = {"input": {"roleId": str(datos["roles"]["ADMINISTRADOR"]),
                         "permissionIds": [str(datos["permisos"]["accounts.read"])]}}
    assert "ADMINISTRADOR" in error_de(ejecutar(GUARDAR, entrada, token))


# ---------------------------------------------------------------------------
# Guardar una columna
# ---------------------------------------------------------------------------

def test_una_columna_cambia_a_todo_el_puesto_y_repetir_no_duplica(datos, capturista_restaurado):
    rol, antes = capturista_restaurado
    token = token_de(datos["ana"]["correo"])
    escritura = datos["permisos"]["accounts.write"]
    deseados = sorted(set(antes) | {escritura})
    entrada = {"input": {"roleId": str(rol), "permissionIds": [str(i) for i in deseados]}}

    # Vista previa: no escribe.
    plan = ejecutar(VISTA_PREVIA, entrada, token)
    assert plan.errors is None, plan.errors
    assert ids_activos(rol) == antes
    if escritura not in antes:
        assert [p["code"] for p in plan.data["previewRolePermissions"]["toActivate"]] == [
            "accounts.write"]
    assert plan.data["previewRolePermissions"]["finalCount"] == len(deseados)

    primero = ejecutar(GUARDAR, entrada, token)
    assert primero.errors is None, primero.errors
    assert primero.data["setRolePermissions"]["changed"] is (escritura not in antes)

    with SessionLocal() as db:
        filas = db.scalar(select(func.count()).select_from(RolePermissionModel).where(
            RolePermissionModel.role_id == rol))

    segundo = ejecutar(GUARDAR, entrada, token)
    assert segundo.errors is None, segundo.errors
    assert segundo.data["setRolePermissions"]["changed"] is False
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(RolePermissionModel).where(
            RolePermissionModel.role_id == rol)) == filas

    # Los dos capturistas lo ven, sin que se tocara su membresía.
    for clave in ("maria", "jose"):
        acceso = ejecutar(MY_ACCESS, token=token_de(datos[clave]["correo"]))
        assert "accounts.write" in acceso.data["myAccess"]["permissions"]


# ---------------------------------------------------------------------------
# Asignar el puesto
# ---------------------------------------------------------------------------

def test_assign_role_deja_un_rol_y_no_toca_isadmin_ni_la_matriz(datos):
    ana = token_de(datos["ana"]["correo"])
    token_pedro = token_de(datos["pedro"]["correo"])  # token emitido siendo CONSULTA
    consulta = datos["roles"]["CONSULTA"]
    columna_consulta = ids_activos(consulta)

    antes = ejecutar(MY_ACCESS, token=token_pedro).data["myAccess"]
    assert "transactions.write" not in antes["permissions"]

    res = ejecutar(ASIGNAR, {"input": {"companyUserId": str(datos["pedro"]["cu"]),
                                       "roleId": str(datos["roles"]["CAPTURISTA"])}}, ana)
    assert res.errors is None, res.errors
    assert res.data["assignRole"] == {"isActive": True,
                                      "role": {"code": "CAPTURISTA", "name": "Capturista"}}

    with SessionLocal() as db:
        activos = db.scalar(select(func.count()).select_from(CompanyUserRoleModel).where(
            CompanyUserRoleModel.company_user_id == datos["pedro"]["cu"],
            CompanyUserRoleModel.is_active.is_(True)))
        assert activos == 1
        assert db.get(CompanyUser, datos["pedro"]["cu"]).is_admin is False

    assert ids_activos(consulta) == columna_consulta

    # Mismo token, siguiente petición: el servidor volvió a leer el rol.
    despues = ejecutar(MY_ACCESS, token=token_pedro).data["myAccess"]
    assert despues["role"]["code"] == "CAPTURISTA"
    assert despues["isAdmin"] is False
    assert "transactions.write" in despues["permissions"]
