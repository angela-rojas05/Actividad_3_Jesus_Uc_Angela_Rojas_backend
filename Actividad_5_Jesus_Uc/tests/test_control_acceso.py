"""Actividad 6 - Control de acceso según el rol (JWT).

Cada persona entra con `login` y usa SU token en el header Authorization.
Las pruebas 5, 6 y 7 forman una secuencia (el mismo token de Pedro antes y
después de que Ana le cambie el rol), por eso dependen del orden del archivo.
"""
import uuid

import jwt
import pytest
from sqlalchemy import func, select

from app.database import Base, SessionLocal, engine
from app.financial_models import Account, AccountConcept, Concept, Transaction
from app.models import (
    Company,
    CompanyUser,
    CompanyUserRoleModel,
    RoleModel,
    User,
)
from app.schema import schema
from app.security import ALGORITHM, JWT_SECRET, hash_password
from app.seed import seed_permissions, seed_role_permissions, seed_roles

PASSWORD = "Secreto123!"

LOGIN = """
mutation($input: LoginInput!) {
  login(input: $input) { token tokenType user { id name email } }
}
"""

CREATE_ACCOUNT = """
mutation($input: CreateAccountInput!) {
  createAccount(input: $input) { id name }
}
"""

CREATE_TX = """
mutation($input: CreateTransactionInput!) {
  createTransaction(input: $input) { id amount }
}
"""

ASSIGN_ROLE = """
mutation($input: AssignRoleInput!) {
  assignRole(input: $input) { id role { code } }
}
"""

ACCOUNTS = """
query($companyId: ID!) { accounts(companyId: $companyId) { id name } }
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


def hacer_login(correo, password=PASSWORD, company_id=None):
    data = {"email": correo, "password": password}
    if company_id is not None:
        data["companyId"] = str(company_id)
    return ejecutar(LOGIN, {"input": data})


def token_de(correo, company_id=None):
    res = hacer_login(correo, company_id=company_id)
    assert res.errors is None, res.errors
    return res.data["login"]["token"]


def contar(modelo, **filtros):
    with SessionLocal() as db:
        stmt = select(func.count()).select_from(modelo)
        for campo, valor in filtros.items():
            stmt = stmt.where(getattr(modelo, campo) == valor)
        return db.scalar(stmt)


def input_cuenta(company_id, nombre):
    return {"input": {"companyId": str(company_id),
                      "accountType": "DEBIT", "name": nombre}}


def input_tx(ids):
    return {"input": {"accountId": str(ids["cuenta"]),
                      "conceptId": str(ids["concepto"]),
                      "transactionType": "INCOME", "amount": "150.50"}}


# ---------------------------------------------------------------------------
# Datos: empresa 1 (Ana, Luis, María, Pedro) y empresa 2 (un admin)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def datos():
    Base.metadata.create_all(engine)
    seed_roles()
    seed_permissions()
    seed_role_permissions()

    suf = uuid.uuid4().hex[:8]
    creados = {"users": [], "cus": [], "companies": []}
    ids = {"suf": suf}

    with SessionLocal() as db:
        roles = {r.code: r.id for r in db.scalars(select(RoleModel)).all()}
        # Asegura que CAPTURISTA esté en su estado base (sin accounts.write)
        capt_id = roles.get("CAPTURISTA")
        if capt_id:
            from app.models import RolePermissionModel, PermissionModel
            acc_write = db.scalar(select(PermissionModel.id).where(PermissionModel.code == "accounts.write"))
            if acc_write:
                rp = db.scalar(select(RolePermissionModel).where(
                    RolePermissionModel.role_id == capt_id,
                    RolePermissionModel.permission_id == acc_write,
                ))
                if rp:
                    rp.is_active = False
                    db.flush()
        emp1 = Company(name=f"Empresa A6 {suf}", is_active=True)
        emp2 = Company(name=f"Empresa A6 dos {suf}", is_active=True)
        db.add_all([emp1, emp2])
        db.flush()
        creados["companies"] = [emp1.id, emp2.id]
        ids["empresa1"], ids["empresa2"] = emp1.id, emp2.id

        def persona(clave, nombre, rol, empresa):
            correo = f"{clave}_{suf}@actividad6.com"
            user = User(name=nombre, email=correo,
                        password_hash=hash_password(PASSWORD), is_active=True)
            db.add(user)
            db.flush()
            cu = CompanyUser(company_id=empresa.id, user_id=user.id,
                             is_admin=(rol == "ADMINISTRADOR"), is_active=True)
            db.add(cu)
            db.flush()
            db.add(CompanyUserRoleModel(company_user_id=cu.id,
                                        role_id=roles[rol], is_active=True))
            creados["users"].append(user.id)
            creados["cus"].append(cu.id)
            ids[clave] = {"correo": correo, "userId": user.id, "cu": cu.id}

        persona("ana", "Ana", "ADMINISTRADOR", emp1)
        persona("luis", "Luis", "CONTADOR", emp1)
        persona("maria", "María", "CAPTURISTA", emp1)
        persona("pedro", "Pedro", "CONSULTA", emp1)
        persona("admin2", "Admin Dos", "ADMINISTRADOR", emp2)

        cuenta = Account(company_id=emp1.id, account_type="DEBIT",
                         name=f"Cuenta A6 {suf}")
        concepto = Concept(company_id=emp1.id, concept_type="INCOME",
                           name=f"Venta A6 {suf}")
        db.add_all([cuenta, concepto])
        db.flush()
        db.add(AccountConcept(account_id=cuenta.id, concept_id=concepto.id))
        db.commit()
        ids["cuenta"], ids["concepto"] = cuenta.id, concepto.id

    estado = {"pedro_token": None}
    yield ids, estado

    with SessionLocal() as db:
        cuentas = [c for c in db.scalars(select(Account.id).where(
            Account.company_id.in_(creados["companies"]))).all()]
        db.query(Transaction).filter(
            Transaction.account_id.in_(cuentas)).delete(
            synchronize_session=False)
        db.query(AccountConcept).filter(
            AccountConcept.account_id.in_(cuentas)).delete(
            synchronize_session=False)
        db.query(Account).filter(Account.id.in_(cuentas)).delete(
            synchronize_session=False)
        db.query(Concept).filter(
            Concept.company_id.in_(creados["companies"])).delete(
            synchronize_session=False)
        db.query(CompanyUserRoleModel).filter(
            CompanyUserRoleModel.company_user_id.in_(creados["cus"])).delete(
            synchronize_session=False)
        db.query(CompanyUser).filter(
            CompanyUser.id.in_(creados["cus"])).delete(
            synchronize_session=False)
        db.query(User).filter(User.id.in_(creados["users"])).delete(
            synchronize_session=False)
        db.query(Company).filter(Company.id.in_(creados["companies"])).delete(
            synchronize_session=False)
        db.commit()


# ---------------------------------------------------------------------------
# Los 9 casos
# ---------------------------------------------------------------------------

def test_caso1_sin_token_no_crea_cuenta(datos):
    ids, _ = datos
    antes = contar(Account)
    res = ejecutar(CREATE_ACCOUNT, input_cuenta(ids["empresa1"], "Sin token"))
    assert res.errors
    assert "Falta el token" in res.errors[0].message
    assert contar(Account) == antes


def test_caso2_maria_capturista_registra_movimiento(datos):
    ids, _ = datos
    token = token_de(ids["maria"]["correo"])
    antes = contar(Transaction)
    res = ejecutar(CREATE_TX, input_tx(ids), token)
    assert res.errors is None, res.errors
    assert contar(Transaction) == antes + 1


def test_caso3_maria_no_puede_crear_cuenta(datos):
    ids, _ = datos
    token = token_de(ids["maria"]["correo"])
    antes = contar(Account)
    res = ejecutar(CREATE_ACCOUNT, input_cuenta(ids["empresa1"], "De María"),
                   token)
    assert res.errors
    assert contar(Account) == antes


def test_caso4_luis_contador_crea_cuenta(datos):
    ids, _ = datos
    token = token_de(ids["luis"]["correo"])
    antes = contar(Account)
    res = ejecutar(CREATE_ACCOUNT, input_cuenta(ids["empresa1"], "De Luis"),
                   token)
    assert res.errors is None, res.errors
    assert contar(Account) == antes + 1


def test_caso5_pedro_consulta_no_registra_movimiento(datos):
    ids, estado = datos
    estado["pedro_token"] = token_de(ids["pedro"]["correo"])
    antes = contar(Transaction)
    res = ejecutar(CREATE_TX, input_tx(ids), estado["pedro_token"])
    assert res.errors
    assert contar(Transaction) == antes


def test_caso6_ana_asigna_capturista_a_pedro(datos):
    ids, _ = datos
    token_ana = token_de(ids["ana"]["correo"])
    with SessionLocal() as db:
        capturista = db.scalar(
            select(RoleModel.id).where(RoleModel.code == "CAPTURISTA"))
    res = ejecutar(ASSIGN_ROLE, {"input": {
        "companyUserId": str(ids["pedro"]["cu"]),
        "roleId": str(capturista)}}, token_ana)
    assert res.errors is None, res.errors
    assert res.data["assignRole"]["role"]["code"] == "CAPTURISTA"


def test_caso7_mismo_token_de_pedro_ahora_si_guarda(datos):
    ids, estado = datos
    assert estado["pedro_token"], "depende del caso 5"
    antes = contar(Transaction)
    res = ejecutar(CREATE_TX, input_tx(ids), estado["pedro_token"])
    assert res.errors is None, res.errors
    assert contar(Transaction) == antes + 1


def test_caso8_token_de_otra_empresa_no_lee_cuentas(datos):
    ids, _ = datos
    token = token_de(ids["admin2"]["correo"])
    res = ejecutar(ACCOUNTS, {"companyId": str(ids["empresa1"])}, token)
    assert res.errors
    assert res.data is None or res.data["accounts"] is None


def test_caso8b_token_de_otra_empresa_no_escribe_cuentas(datos):
    ids, _ = datos
    token = token_de(ids["admin2"]["correo"])
    antes = contar(Account)
    res = ejecutar(CREATE_ACCOUNT, input_cuenta(ids["empresa1"], "Intrusa"),
                   token)
    assert res.errors
    assert contar(Account) == antes


def test_caso9_token_alterado_rechazado(datos):
    ids, _ = datos
    token = token_de(ids["luis"]["correo"])
    i = len(token) - 6  # dentro de la firma
    otra = "A" if token[i] != "A" else "B"
    alterado = token[:i] + otra + token[i + 1:]
    antes = contar(Account)
    res = ejecutar(CREATE_ACCOUNT, input_cuenta(ids["empresa1"], "Alterado"),
                   alterado)
    assert res.errors
    assert "no es válido" in res.errors[0].message
    assert contar(Account) == antes


def test_caso9_token_vencido_rechazado(datos):
    from datetime import datetime, timedelta, timezone
    ids, _ = datos
    vencido = jwt.encode({
        "companyUserId": ids["luis"]["cu"],
        "companyId": ids["empresa1"],
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
    }, JWT_SECRET, algorithm=ALGORITHM)
    antes = contar(Account)
    res = ejecutar(CREATE_ACCOUNT, input_cuenta(ids["empresa1"], "Vencido"),
                   vencido)
    assert res.errors
    assert "no es válido" in res.errors[0].message
    assert contar(Account) == antes


# ---------------------------------------------------------------------------
# Extras
# ---------------------------------------------------------------------------

def test_payload_sin_password_ni_permisos(datos):
    ids, _ = datos
    token = token_de(ids["ana"]["correo"])
    payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    assert set(payload) == {"companyUserId", "companyId", "exp"}
    assert payload["companyUserId"] == ids["ana"]["cu"]
    assert payload["companyId"] == ids["empresa1"]


def test_login_devuelve_bearer_minuscula_y_usuario(datos):
    ids, _ = datos
    res = hacer_login(ids["ana"]["correo"])
    assert res.errors is None
    assert res.data["login"]["tokenType"] == "bearer"
    assert set(res.data["login"]["user"]) == {"id", "name", "email"}


def test_login_incorrecto_no_entrega_token(datos):
    ids, _ = datos
    res = hacer_login(ids["ana"]["correo"], password="Incorrecta999!")
    assert res.errors
    assert res.data is None or res.data["login"] is None
    res = hacer_login("noexiste@actividad6.com")
    assert res.errors
    assert res.data is None or res.data["login"] is None


def test_login_no_expone_hash(datos):
    ids, _ = datos
    consulta = LOGIN.replace("email }", "email passwordHash }")
    res = ejecutar(consulta, {"input": {"email": ids["ana"]["correo"],
                                        "password": PASSWORD}})
    assert res.errors  # el campo passwordHash no existe en el esquema
    sdl = schema.as_str()
    assert "passwordHash" not in sdl and "password_hash" not in sdl


def test_login_con_company_id_de_otra_empresa_falla(datos):
    ids, _ = datos
    res = hacer_login(ids["ana"]["correo"], company_id=ids["empresa2"])
    assert res.errors


def test_actor_company_user_id_ya_no_existe(datos):
    ids, _ = datos
    token = token_de(ids["luis"]["correo"])
    q = """
    mutation($input: CreateAccountInput!) {
      createAccount(actorCompanyUserId: 1, input: $input) { id }
    }
    """
    antes = contar(Account)
    res = ejecutar(q, input_cuenta(ids["empresa1"], "Con actor"), token)
    assert res.errors
    assert "actorCompanyUserId" in res.errors[0].message
    assert contar(Account) == antes
