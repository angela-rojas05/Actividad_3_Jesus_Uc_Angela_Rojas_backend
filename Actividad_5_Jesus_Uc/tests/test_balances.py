"""Actividad 7 - Balances por cuenta y general.

Los resultados esperados están escritos a mano a partir de los datos de
entrada (tabla de la guía); no se usa el servicio de balances para
calcularlos.  Los movimientos de referencia se insertan directo en la BD y
cada empresa/cuenta de prueba es nueva, así que las pruebas no dependen de
los datos de demo y no se estorban entre sí.

Casos automatizados: B01, B02, B03, B04, B05, B06, B10, B11, B12, B13 y B15
(más la validación de montos).
"""
import uuid
from datetime import datetime
from decimal import Decimal

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
from app.security import hash_password
from app.seed import seed_permissions, seed_role_permissions, seed_roles

PASSWORD = "Secreto123!"

LOGIN = """
mutation($input: LoginInput!) {
  login(input: $input) { token }
}
"""

CREATE_TX = """
mutation($input: CreateTransactionInput!) {
  createTransaction(input: $input) {
    id amount transactionDate capturedAt
  }
}
"""

ACCOUNT_BALANCE = """
query($accountId: ID!, $from: Date!, $to: Date!) {
  accountBalance(accountId: $accountId, fromDate: $from, toDate: $to) {
    accountId accountName isActive openingBalance totalIncome totalExpense
    profit closingBalance isInRed
  }
}
"""

GENERAL_BALANCE = """
query($from: Date!, $to: Date!) {
  generalBalance(fromDate: $from, toDate: $to) {
    companyId currency fromDate toDate openingBalance totalIncome
    totalExpense profit closingBalance isInRed accountsInRed
    accounts {
      accountId accountName isActive openingBalance totalIncome totalExpense
      profit closingBalance isInRed
    }
  }
}
"""

PERIODO = {"from": "2026-10-26", "to": "2026-10-30"}


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


def balance_cuenta(token, cuenta_id, desde="2026-10-26", hasta="2026-10-30"):
    res = ejecutar(
        ACCOUNT_BALANCE,
        {"accountId": str(cuenta_id), "from": desde, "to": hasta},
        token,
    )
    assert res.errors is None, res.errors
    return res.data["accountBalance"]


def balance_general(token, desde="2026-10-26", hasta="2026-10-30"):
    res = ejecutar(GENERAL_BALANCE, {"from": desde, "to": hasta}, token)
    assert res.errors is None, res.errors
    return res.data["generalBalance"]


def resumen(b):
    """Los seis importes de un balance, en el orden de la tabla de la guía."""
    return (
        b["openingBalance"], b["totalIncome"], b["totalExpense"],
        b["profit"], b["closingBalance"], b["isInRed"],
    )


def contar_transacciones():
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(Transaction))


def capturar(token, cuenta, concepto, tipo, monto, fecha=None):
    entrada = {
        "accountId": str(cuenta), "conceptId": str(concepto),
        "transactionType": tipo, "amount": monto,
    }
    if fecha is not None:
        entrada["transactionDate"] = fecha
    return ejecutar(CREATE_TX, {"input": entrada}, token)


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def datos():
    Base.metadata.create_all(engine)
    seed_roles()
    seed_permissions()
    seed_role_permissions()

    suf = uuid.uuid4().hex[:8]
    creados = {"users": [], "cus": [], "companies": []}
    ids = {}

    with SessionLocal() as db:
        roles = {r.code: r.id for r in db.scalars(select(RoleModel)).all()}

        def empresa(nombre):
            e = Company(name=f"{nombre} {suf}", is_active=True)
            db.add(e)
            db.flush()
            creados["companies"].append(e.id)
            return e

        def persona(clave, rol, emp):
            correo = f"{clave}_{suf}@actividad7.com"
            user = User(name=clave, email=correo,
                        password_hash=hash_password(PASSWORD), is_active=True)
            db.add(user)
            db.flush()
            cu = CompanyUser(company_id=emp.id, user_id=user.id,
                             is_admin=(rol == "ADMINISTRADOR"), is_active=True)
            db.add(cu)
            db.flush()
            db.add(CompanyUserRoleModel(company_user_id=cu.id,
                                        role_id=roles[rol], is_active=True))
            creados["users"].append(user.id)
            creados["cus"].append(cu.id)
            ids[clave] = {"correo": correo, "userId": user.id}

        def cuenta(emp, nombre, con_conceptos=None):
            c = Account(company_id=emp.id, account_type="DEBIT", name=nombre)
            db.add(c)
            db.flush()
            for concepto in con_conceptos or []:
                db.add(AccountConcept(account_id=c.id,
                                      concept_id=concepto.id))
            db.flush()
            return c

        def concepto(emp, tipo, nombre):
            c = Concept(company_id=emp.id, concept_type=tipo, name=nombre)
            db.add(c)
            db.flush()
            return c

        emp_a = empresa("Empresa A7 A")
        emp_b = empresa("Empresa A7 B")
        emp_c = empresa("Empresa A7 C")  # sin cuentas
        ids["empresaA"], ids["empresaB"], ids["empresaC"] = (
            emp_a.id, emp_b.id, emp_c.id)

        persona("ana", "ADMINISTRADOR", emp_a)
        persona("pedro", "CONSULTA", emp_a)
        persona("adminb", "ADMINISTRADOR", emp_b)
        persona("adminc", "ADMINISTRADOR", emp_c)

        ing_a = concepto(emp_a, "INCOME", "Ingreso")
        egr_a = concepto(emp_a, "EXPENSE", "Egreso")
        banco = cuenta(emp_a, "Banco", [ing_a, egr_a])
        caja = cuenta(emp_a, "Caja", [ing_a, egr_a])
        ahorro = cuenta(emp_a, "Ahorro")
        ids["banco"], ids["caja"], ids["ahorro"] = banco.id, caja.id, ahorro.id
        ids["ingresoA"], ids["egresoA"] = ing_a.id, egr_a.id

        # Conjunto de referencia de la guía (todo a las 12:00:00Z).
        referencia = [
            (banco, ing_a, "INCOME", "1000.00", datetime(2026, 10, 25, 12)),
            (banco, ing_a, "INCOME", "3000.00", datetime(2026, 10, 26, 12)),
            (banco, egr_a, "EXPENSE", "1200.00", datetime(2026, 10, 27, 12)),
            (banco, egr_a, "EXPENSE", "1000.00", datetime(2026, 10, 28, 12)),
            (caja, ing_a, "INCOME", "500.00", datetime(2026, 10, 26, 12)),
            (caja, egr_a, "EXPENSE", "700.00", datetime(2026, 10, 29, 12)),
        ]
        capturista = ids["ana"]["userId"]
        for c, con, tipo, monto, fecha in referencia:
            db.add(Transaction(
                account_id=c.id, concept_id=con.id, transaction_type=tipo,
                amount=Decimal(monto), transaction_date=fecha,
                captured_by=capturista))

        # Empresa B: una cuenta vacía por caso para que no se estorben.
        ing_b = concepto(emp_b, "INCOME", "Ingreso")
        egr_b = concepto(emp_b, "EXPENSE", "Egreso")
        ids["ingresoB"], ids["egresoB"] = ing_b.id, egr_b.id
        for caso in ("b04", "b05", "b06", "b15", "monto", "ajena"):
            ids[caso] = cuenta(emp_b, f"Cuenta {caso}", [ing_b, egr_b]).id
        db.commit()

    yield ids

    with SessionLocal() as db:
        cuentas = db.scalars(select(Account.id).where(
            Account.company_id.in_(creados["companies"]))).all()
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
# B01 / B02 / B03: tabla de referencia
# ---------------------------------------------------------------------------

def test_b01_balances_coinciden_con_la_tabla_de_referencia(datos):
    token = token_de(datos["ana"]["correo"])
    antes = contar_transacciones()

    # saldo inicial, ingresos, egresos, profit, saldo final, en rojo
    assert resumen(balance_cuenta(token, datos["banco"])) == (
        "1000.00", "3000.00", "2200.00", "800.00", "1800.00", False)
    assert resumen(balance_cuenta(token, datos["caja"])) == (
        "0.00", "500.00", "700.00", "-200.00", "-200.00", True)
    assert resumen(balance_cuenta(token, datos["ahorro"])) == (
        "0.00", "0.00", "0.00", "0.00", "0.00", False)

    general = balance_general(token)
    assert general["currency"] == "MXN"
    assert general["companyId"] == str(datos["empresaA"])
    assert general["fromDate"] == "2026-10-26"
    assert general["toDate"] == "2026-10-30"
    assert resumen(general) == (
        "1000.00", "3500.00", "2900.00", "600.00", "1600.00", False)
    assert general["accountsInRed"] == 1

    # Detalle ordenado por accountId y con las tres cuentas (Ahorro incluida).
    assert [a["accountName"] for a in general["accounts"]] == [
        "Banco", "Caja", "Ahorro"]
    ids_detalle = [int(a["accountId"]) for a in general["accounts"]]
    assert ids_detalle == sorted(ids_detalle)

    # Las igualdades de la Parte 3.
    cuentas = general["accounts"]
    d = Decimal
    assert d(general["profit"]) == d(general["totalIncome"]) - d(general["totalExpense"])
    assert d(general["closingBalance"]) == d(general["openingBalance"]) + d(general["profit"])
    assert d(general["closingBalance"]) == sum(d(a["closingBalance"]) for a in cuentas)
    assert general["accountsInRed"] == sum(1 for a in cuentas if d(a["closingBalance"]) < 0)

    # Consultar no crea ni modifica movimientos.
    assert contar_transacciones() == antes


def test_b02_banco_solo_el_28_profit_negativo_sin_numeros_rojos(datos):
    token = token_de(datos["ana"]["correo"])
    banco = balance_cuenta(token, datos["banco"], "2026-10-28", "2026-10-28")
    assert resumen(banco) == (
        "2800.00", "0.00", "1000.00", "-1000.00", "1800.00", False)


def test_b03_empresa_sin_cuentas_devuelve_lista_vacia_y_ceros(datos):
    token = token_de(datos["adminc"]["correo"])
    general = balance_general(token)
    assert general["accounts"] == []
    assert resumen(general) == (
        "0.00", "0.00", "0.00", "0.00", "0.00", False)
    assert general["accountsInRed"] == 0


# ---------------------------------------------------------------------------
# B04: bordes del periodo (y fecha con zona horaria normalizada a UTC)
# ---------------------------------------------------------------------------

def test_b04_bordes_del_periodo(datos):
    token = token_de(datos["adminb"]["correo"])
    cuenta, ing, egr = datos["b04"], datos["ingresoB"], datos["egresoB"]

    for tipo, concepto, monto, fecha in [
        ("INCOME", ing, "1.00", "2026-10-25T23:59:59Z"),    # solo saldo inicial
        ("INCOME", ing, "10.00", "2026-10-26T00:00:00Z"),   # entra (inicio incluido)
        ("EXPENSE", egr, "4.00", "2026-10-30T23:59:59Z"),   # entra
        ("INCOME", ing, "100.00", "2026-10-31T00:00:00Z"),  # fuera (fin excluido)
    ]:
        res = capturar(token, cuenta, concepto, tipo, monto, fecha)
        assert res.errors is None, res.errors

    assert resumen(balance_cuenta(token, cuenta)) == (
        "1.00", "10.00", "4.00", "6.00", "7.00", False)


def test_b04_una_fecha_con_zona_se_normaliza_a_utc(datos):
    token = token_de(datos["adminb"]["correo"])
    # 2026-10-30T17:59:59-06:00 == 2026-10-30T23:59:59Z (dentro del periodo)
    res = capturar(token, datos["b04"], datos["egresoB"], "EXPENSE", "2.00",
                   "2026-10-30T17:59:59-06:00")
    assert res.errors is None, res.errors
    assert res.data["createTransaction"]["transactionDate"] == "2026-10-30T23:59:59Z"
    # 2026-10-30T19:00:00-06:00 == 2026-10-31T01:00:00Z (fuera del periodo)
    res = capturar(token, datos["b04"], datos["egresoB"], "EXPENSE", "50.00",
                   "2026-10-30T19:00:00-06:00")
    assert res.errors is None, res.errors

    # Antes: egresos 4.00; ahora 4.00 + 2.00 y el de 50.00 no participa.
    assert resumen(balance_cuenta(token, datos["b04"])) == (
        "1.00", "10.00", "6.00", "4.00", "5.00", False)


# ---------------------------------------------------------------------------
# B05: el periodo usa transactionDate, no capturedAt
# ---------------------------------------------------------------------------

def test_b05_participa_segun_transaction_date_no_captured_at(datos):
    token = token_de(datos["adminb"]["correo"])
    res = capturar(token, datos["b05"], datos["egresoB"], "EXPENSE", "75.00",
                   "2026-10-27T12:00:00Z")
    assert res.errors is None, res.errors
    mov = res.data["createTransaction"]
    # capturedAt lo pone el servidor (ahora), muy posterior al 27/10/2026.
    assert mov["transactionDate"] == "2026-10-27T12:00:00Z"
    assert mov["capturedAt"] != mov["transactionDate"]

    assert resumen(balance_cuenta(token, datos["b05"], "2026-10-27", "2026-10-27")) == (
        "0.00", "0.00", "75.00", "-75.00", "-75.00", True)
    # Un día antes no participa aunque se haya capturado "después".
    assert resumen(balance_cuenta(token, datos["b05"], "2026-10-26", "2026-10-26")) == (
        "0.00", "0.00", "0.00", "0.00", "0.00", False)


# ---------------------------------------------------------------------------
# B06: centavos exactos (0.10 + 0.20 - 0.30 = 0.00, no 5.55e-17)
# ---------------------------------------------------------------------------

def test_b06_centavos_exactos(datos):
    token = token_de(datos["adminb"]["correo"])
    cuenta, ing, egr = datos["b06"], datos["ingresoB"], datos["egresoB"]
    for tipo, concepto, monto in [
        ("INCOME", ing, "0.10"), ("INCOME", ing, "0.20"), ("EXPENSE", egr, "0.30"),
    ]:
        res = capturar(token, cuenta, concepto, tipo, monto, "2026-10-27T12:00:00Z")
        assert res.errors is None, res.errors

    assert resumen(balance_cuenta(token, cuenta)) == (
        "0.00", "0.30", "0.30", "0.00", "0.00", False)


# ---------------------------------------------------------------------------
# B10 / B11 / B12 / B13: errores y acceso
# ---------------------------------------------------------------------------

def test_b10_from_posterior_a_to_no_devuelve_balance(datos):
    token = token_de(datos["ana"]["correo"])
    res = ejecutar(ACCOUNT_BALANCE, {
        "accountId": str(datos["banco"]), "from": "2026-10-30", "to": "2026-10-26"
    }, token)
    assert res.errors and res.data is None
    res = ejecutar(GENERAL_BALANCE, {"from": "2026-10-30", "to": "2026-10-26"}, token)
    assert res.errors and res.data is None
    # Fecha inexistente: la rechaza el escalar Date.
    res = ejecutar(GENERAL_BALANCE, {"from": "2026-02-31", "to": "2026-03-01"}, token)
    assert res.errors and res.data is None
    # Un solo día sí es válido.
    assert balance_cuenta(token, datos["banco"], "2026-10-26", "2026-10-26")


def test_b11_sin_token_o_token_alterado_se_rechaza(datos):
    token = token_de(datos["ana"]["correo"])
    alterado = token[:-3] + ("AAA" if not token.endswith("AAA") else "BBB")
    for t in (None, "basura", alterado):
        res = ejecutar(ACCOUNT_BALANCE, {
            "accountId": str(datos["banco"]), **PERIODO}, t)
        assert res.errors and res.data is None
        res = ejecutar(GENERAL_BALANCE, PERIODO, t)
        assert res.errors and res.data is None


def test_b12_cuenta_de_otra_empresa_no_revela_datos(datos):
    token_a = token_de(datos["ana"]["correo"])
    ajena = ejecutar(ACCOUNT_BALANCE, {
        "accountId": str(datos["ajena"]), **{"from": "2026-10-26", "to": "2026-10-30"}
    }, token_a)
    inexistente = ejecutar(ACCOUNT_BALANCE, {
        "accountId": "99999999", **{"from": "2026-10-26", "to": "2026-10-30"}
    }, token_a)
    assert ajena.data is None and inexistente.data is None
    # Mismo mensaje en ambos casos y sin nombres ni importes de la otra empresa.
    assert ajena.errors[0].message == inexistente.errors[0].message == "Cuenta no disponible."

    # El general de A solo trae cuentas de A.
    general = balance_general(token_a)
    assert {a["accountName"] for a in general["accounts"]} == {"Banco", "Caja", "Ahorro"}
    assert general["companyId"] == str(datos["empresaA"])


def test_b13_consulta_lee_balances_pero_no_captura(datos):
    token = token_de(datos["pedro"]["correo"])
    assert resumen(balance_cuenta(token, datos["banco"])) == (
        "1000.00", "3000.00", "2200.00", "800.00", "1800.00", False)
    assert balance_general(token)["accountsInRed"] == 1

    antes = contar_transacciones()
    res = capturar(token, datos["banco"], datos["ingresoA"], "INCOME", "10.00")
    assert res.errors
    assert contar_transacciones() == antes


# ---------------------------------------------------------------------------
# B15 y precisión del monto
# ---------------------------------------------------------------------------

def test_b15_egreso_en_cuenta_vacia_deja_saldo_negativo(datos):
    token = token_de(datos["adminb"]["correo"])
    res = capturar(token, datos["b15"], datos["egresoB"], "EXPENSE", "50.00",
                   "2026-10-27T12:00:00Z")
    assert res.errors is None, res.errors
    # El monto guardado sigue siendo positivo; el tipo EXPENSE es el que resta.
    assert res.data["createTransaction"]["amount"] == "50.00"

    cuenta = balance_cuenta(token, datos["b15"])
    assert resumen(cuenta) == ("0.00", "0.00", "50.00", "-50.00", "-50.00", True)
    general = balance_general(token)
    assert general["isInRed"] is True
    assert general["accountsInRed"] >= 1


@pytest.mark.parametrize("monto", ["0.001", "10.555", "0", "-5.00", "NaN", "Infinity"])
def test_monto_invalido_se_rechaza_sin_crear_fila(datos, monto):
    token = token_de(datos["adminb"]["correo"])
    antes = contar_transacciones()
    res = capturar(token, datos["monto"], datos["ingresoB"], "INCOME", monto)
    assert res.errors
    assert contar_transacciones() == antes


def test_monto_con_dos_decimales_o_menos_se_acepta(datos):
    token = token_de(datos["adminb"]["correo"])
    res = capturar(token, datos["monto"], datos["ingresoB"], "INCOME", "10.50")
    assert res.errors is None, res.errors
    assert res.data["createTransaction"]["amount"] == "10.50"
