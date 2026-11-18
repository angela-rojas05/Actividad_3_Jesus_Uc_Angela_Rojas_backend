"""Unidad III, Actividad 2 - Idempotencia y API del dashboard administrativo.

Parte 1: createTransaction con idempotencyKey.
Parte 2: lo que el dashboard administrativo lee y escribe (myAccess,
companyUsers con rol, altas y bajas lógicas).

Cada corrida crea sus propias empresas y personas (sufijo aleatorio) y las
borra al terminar, así que no depende de los datos de la demo.
"""
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select

from app.database import Base, SessionLocal, engine
from app.financial_models import (
    Account,
    AccountConcept,
    Concept,
    IdempotencyKey,
    Transaction,
)
from app.models import Company, CompanyUser, CompanyUserRoleModel, RoleModel, User
from app.schema import schema
from app.security import hash_password
from app.seed import seed_permissions, seed_role_permissions, seed_roles

PASSWORD = "Secreto123!"

LOGIN = """
mutation($input: LoginInput!) { login(input: $input) { token } }
"""

CREATE_TX = """
mutation($input: CreateTransactionInput!) {
  createTransaction(input: $input) { id amount transactionType }
}
"""

MY_ACCESS = """
query { myAccess { companyUserId companyId companyName userName isAdmin
                   role { code name } permissions } }
"""

COMPANY_USERS = """
query($companyId: ID!) {
  companyUsers(companyId: $companyId) {
    id isAdmin isActive role { code name } user { name email }
  }
}
"""

CREATE_USER = """
mutation($input: CreateCompanyUserInput!) {
  createCompanyUser(input: $input) { id isAdmin isActive role { code } user { email } }
}
"""

DEACTIVATE_USER = """
mutation($id: ID!) { deactivateCompanyUser(id: $id) { id isActive } }
"""

CREATE_ACCOUNT = """
mutation($input: CreateAccountInput!) {
  createAccount(input: $input) { id name accountType isActive }
}
"""

REMOVE_CONCEPT = """
mutation($a: ID!, $c: ID!) { removeConceptFromAccount(accountId: $a, conceptId: $c) }
"""


class FakeRequest:
    def __init__(self, token=None):
        self.headers = {}
        if token is not None:
            self.headers["authorization"] = f"Bearer {token}"


def ejecutar(query, variables=None, token=None):
    return schema.execute_sync(
        query,
        variable_values=variables or {},
        context_value={"request": FakeRequest(token)},
    )


def token_de(correo):
    res = ejecutar(LOGIN, {"input": {"email": correo, "password": PASSWORD}})
    assert res.errors is None, res.errors
    return res.data["login"]["token"]


def contar(modelo, *condiciones):
    with SessionLocal() as db:
        stmt = select(func.count()).select_from(modelo)
        for condicion in condiciones:
            stmt = stmt.where(condicion)
        return db.scalar(stmt)


@pytest.fixture(scope="module")
def datos():
    Base.metadata.create_all(engine)
    seed_roles()
    seed_permissions()
    seed_role_permissions()

    suf = uuid.uuid4().hex[:8]
    ids = {"suf": suf, "companies": []}

    with SessionLocal() as db:
        roles = {r.code: r.id for r in db.scalars(select(RoleModel)).all()}

        def empresa(nombre):
            e = Company(name=f"{nombre} {suf}", is_active=True)
            db.add(e)
            db.flush()
            ids["companies"].append(e.id)
            return e

        def persona(clave, rol, emp):
            correo = f"{clave}_{suf}@u3a2.com"
            user = User(name=clave.capitalize(), email=correo,
                        password_hash=hash_password(PASSWORD), is_active=True)
            db.add(user)
            db.flush()
            cu = CompanyUser(company_id=emp.id, user_id=user.id,
                             is_admin=(rol == "ADMINISTRADOR"), is_active=True)
            db.add(cu)
            db.flush()
            db.add(CompanyUserRoleModel(company_user_id=cu.id,
                                        role_id=roles[rol], is_active=True))
            ids[clave] = {"correo": correo, "cu": cu.id}

        emp_a = empresa("Empresa U3A2 A")
        emp_b = empresa("Empresa U3A2 B")
        ids["empresaA"], ids["empresaB"] = emp_a.id, emp_b.id

        persona("ana", "ADMINISTRADOR", emp_a)
        persona("pedro", "CONSULTA", emp_a)
        persona("adminb", "ADMINISTRADOR", emp_b)

        for clave, emp in (("A", emp_a), ("B", emp_b)):
            egreso = Concept(company_id=emp.id, concept_type="EXPENSE", name="Renta")
            db.add(egreso)
            db.flush()
            cuenta = Account(company_id=emp.id, account_type="DEBIT", name="Banco")
            db.add(cuenta)
            db.flush()
            db.add(AccountConcept(account_id=cuenta.id, concept_id=egreso.id))
            ids[f"cuenta{clave}"], ids[f"egreso{clave}"] = cuenta.id, egreso.id
        db.commit()

    yield ids

    with SessionLocal() as db:
        cuentas = db.scalars(select(Account.id).where(
            Account.company_id.in_(ids["companies"]))).all()
        # Las llaves se van con su movimiento (ON DELETE CASCADE).
        db.query(Transaction).filter(Transaction.account_id.in_(cuentas)).delete(
            synchronize_session=False)
        db.query(Company).filter(Company.id.in_(ids["companies"])).delete(
            synchronize_session=False)
        db.query(User).filter(User.email.like(f"%{suf}@u3a2.com")).delete(
            synchronize_session=False)
        db.commit()


def egreso(datos, llave=None, monto="100.00", cuenta="A"):
    entrada = {
        "accountId": str(datos[f"cuenta{cuenta}"]),
        "conceptId": str(datos[f"egreso{cuenta}"]),
        "transactionType": "EXPENSE",
        "amount": monto,
    }
    if llave is not None:
        entrada["idempotencyKey"] = llave
    return {"input": entrada}


# ---------------------------------------------------------------------------
# Parte 1: idempotencia
# ---------------------------------------------------------------------------

def test_misma_llave_devuelve_el_mismo_movimiento(datos):
    token = token_de(datos["ana"]["correo"])
    llave = f"llave-misma-{uuid.uuid4()}"
    antes = contar(Transaction)

    primero = ejecutar(CREATE_TX, egreso(datos, llave), token)
    reintento = ejecutar(CREATE_TX, egreso(datos, llave), token)

    assert primero.errors is None, primero.errors
    assert reintento.errors is None, reintento.errors
    assert reintento.data == primero.data
    assert contar(Transaction) == antes + 1
    assert contar(IdempotencyKey, IdempotencyKey.idempotency_key == llave) == 1


def test_otra_llave_crea_otro_movimiento_aunque_el_monto_coincida(datos):
    token = token_de(datos["ana"]["correo"])
    antes = contar(Transaction)

    uno = ejecutar(CREATE_TX, egreso(datos, f"llave-1-{uuid.uuid4()}"), token)
    dos = ejecutar(CREATE_TX, egreso(datos, f"llave-2-{uuid.uuid4()}"), token)

    assert uno.errors is None and dos.errors is None
    assert uno.data["createTransaction"]["id"] != dos.data["createTransaction"]["id"]
    assert contar(Transaction) == antes + 2


def test_misma_llave_con_otros_datos_se_rechaza(datos):
    token = token_de(datos["ana"]["correo"])
    llave = f"llave-datos-{uuid.uuid4()}"
    assert ejecutar(CREATE_TX, egreso(datos, llave, "100.00"), token).errors is None
    antes = contar(Transaction)

    otro = ejecutar(CREATE_TX, egreso(datos, llave, "250.00"), token)

    assert otro.errors is not None
    assert "ya se usó con otros datos" in otro.errors[0].message
    assert contar(Transaction) == antes


def test_sin_llave_cada_envio_es_nuevo(datos):
    token = token_de(datos["ana"]["correo"])
    antes = contar(Transaction)
    assert ejecutar(CREATE_TX, egreso(datos), token).errors is None
    assert ejecutar(CREATE_TX, egreso(datos), token).errors is None
    assert contar(Transaction) == antes + 2


def test_llave_demasiado_corta_se_rechaza(datos):
    token = token_de(datos["ana"]["correo"])
    res = ejecutar(CREATE_TX, egreso(datos, "abc"), token)
    assert res.errors is not None
    assert "idempotencyKey" in res.errors[0].message


def test_reintento_tras_quitar_el_concepto_devuelve_el_movimiento(datos):
    """Si el COMMIT pasó, el reintento encuentra la llave aunque las reglas cambien."""
    token = token_de(datos["ana"]["correo"])
    llave = f"llave-regla-{uuid.uuid4()}"
    primero = ejecutar(CREATE_TX, egreso(datos, llave), token)
    assert primero.errors is None

    quitar = ejecutar(REMOVE_CONCEPT, {"a": str(datos["cuentaA"]),
                                       "c": str(datos["egresoA"])}, token)
    assert quitar.errors is None
    try:
        reintento = ejecutar(CREATE_TX, egreso(datos, llave), token)
        assert reintento.errors is None, reintento.errors
        assert reintento.data == primero.data
    finally:
        with SessionLocal() as db:
            db.query(AccountConcept).filter(
                AccountConcept.account_id == datos["cuentaA"]).update({"is_active": True})
            db.commit()


def test_la_llave_es_por_empresa(datos):
    llave = f"llave-empresa-{uuid.uuid4()}"
    a = ejecutar(CREATE_TX, egreso(datos, llave), token_de(datos["ana"]["correo"]))
    b = ejecutar(CREATE_TX, egreso(datos, llave, cuenta="B"),
                 token_de(datos["adminb"]["correo"]))
    assert a.errors is None and b.errors is None
    assert a.data["createTransaction"]["id"] != b.data["createTransaction"]["id"]


def test_reintentos_simultaneos_dejan_un_solo_movimiento(datos):
    """Cinco envíos a la vez con la misma llave: el índice único deja uno."""
    token = token_de(datos["ana"]["correo"])
    llave = f"llave-carrera-{uuid.uuid4()}"
    antes = contar(Transaction)

    with ThreadPoolExecutor(max_workers=5) as pool:
        resultados = list(pool.map(
            lambda _: ejecutar(CREATE_TX, egreso(datos, llave), token), range(5)))

    assert all(r.errors is None for r in resultados), [r.errors for r in resultados]
    assert len({r.data["createTransaction"]["id"] for r in resultados}) == 1
    assert contar(Transaction) == antes + 1


# ---------------------------------------------------------------------------
# Parte 2: API del dashboard administrativo
# ---------------------------------------------------------------------------

def test_my_access_sale_de_la_bd(datos):
    ana = ejecutar(MY_ACCESS, token=token_de(datos["ana"]["correo"]))
    pedro = ejecutar(MY_ACCESS, token=token_de(datos["pedro"]["correo"]))
    assert ana.errors is None and pedro.errors is None

    a = ana.data["myAccess"]
    assert a["companyId"] == str(datos["empresaA"])
    assert a["isAdmin"] is True
    assert a["role"]["code"] == "ADMINISTRADOR"
    assert "company.users.write" in a["permissions"]

    p = pedro.data["myAccess"]
    assert p["role"]["code"] == "CONSULTA"
    assert "company.users.read" in p["permissions"]
    assert not any(c.endswith(".write") for c in p["permissions"])


def test_my_access_sin_token():
    res = ejecutar(MY_ACCESS)
    assert res.errors is not None
    assert res.errors[0].message == "Falta el token"


def test_company_users_trae_el_rol_y_nunca_la_contrasena(datos):
    res = ejecutar(COMPANY_USERS, {"companyId": str(datos["empresaA"])},
                   token_de(datos["pedro"]["correo"]))
    assert res.errors is None, res.errors
    filas = {f["user"]["email"]: f for f in res.data["companyUsers"]}
    assert filas[datos["ana"]["correo"]]["role"]["code"] == "ADMINISTRADOR"
    assert filas[datos["pedro"]["correo"]]["role"]["code"] == "CONSULTA"

    campos_user = {c.name for c in schema.get_type_by_name("User").fields}
    assert not any("password" in c.lower() for c in campos_user)


def test_alta_y_baja_logica_de_usuario(datos):
    token = token_de(datos["ana"]["correo"])
    correo = f"nuevo_{datos['suf']}@u3a2.com"
    entrada = {"input": {"companyId": str(datos["empresaA"]), "name": "Nuevo",
                         "email": correo, "password": PASSWORD}}

    alta = ejecutar(CREATE_USER, entrada, token)
    assert alta.errors is None, alta.errors
    nuevo = alta.data["createCompanyUser"]
    assert nuevo["isAdmin"] is False and nuevo["isActive"] is True
    assert nuevo["role"]["code"] == "CONSULTA"

    duplicado = ejecutar(CREATE_USER, entrada, token)
    assert duplicado.errors[0].message == "El correo electrónico ya está registrado."

    baja = ejecutar(DEACTIVATE_USER, {"id": nuevo["id"]}, token)
    assert baja.errors is None, baja.errors
    assert baja.data["deactivateCompanyUser"]["isActive"] is False
    # La fila sigue en MySQL, solo inactiva.
    assert contar(CompanyUser, CompanyUser.id == int(nuevo["id"]),
                  CompanyUser.is_active.is_(False)) == 1


def test_no_se_desactiva_al_administrador_principal(datos):
    res = ejecutar(DEACTIVATE_USER, {"id": str(datos["ana"]["cu"])},
                   token_de(datos["ana"]["correo"]))
    assert res.errors is not None
    assert "administrador principal" in res.errors[0].message


def test_consulta_no_puede_dar_de_alta(datos):
    token = token_de(datos["pedro"]["correo"])
    cuenta = ejecutar(CREATE_ACCOUNT, {"input": {
        "companyId": str(datos["empresaA"]), "accountType": "CASH", "name": "Caja Pedro"}}, token)
    assert cuenta.errors is not None
    assert "accounts.write" in cuenta.errors[0].message
