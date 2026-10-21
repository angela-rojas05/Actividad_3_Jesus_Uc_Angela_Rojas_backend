"""Actividad 6 - Evidencias: ejecuta los 9 casos contra el servidor real.

Requisitos: MySQL y uvicorn corriendo, y haber ejecutado antes
`python scripts/preparar_demo_actividad6.py`.

Nunca imprime el secreto ni un token completo (solo 15 caracteres + "...").
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import requests
from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app.financial_models import Account, Transaction  # noqa: E402
from app.security import ALGORITHM, JWT_SECRET  # noqa: E402

URL = "http://127.0.0.1:8000/graphql"
IDS = json.loads((ROOT / "scripts" / "ids_demo.json").read_text("utf-8"))
PASSWORD = IDS["password"]
P = IDS["personas"]

LOGIN = """mutation($input: LoginInput!) {
  login(input: $input) { token tokenType user { id name email } } }"""
CREATE_ACCOUNT = """mutation($input: CreateAccountInput!) {
  createAccount(input: $input) { id name } }"""
CREATE_TX = """mutation($input: CreateTransactionInput!) {
  createTransaction(input: $input) { id amount } }"""
ASSIGN_ROLE = """mutation($input: AssignRoleInput!) {
  assignRole(input: $input) { id role { code } } }"""
ACCOUNTS = """query($companyId: ID!) { accounts(companyId: $companyId) { id name } }"""
ROLES = """query { roles { id code } }"""


def corto(token):
    return token[:15] + "..."


def filas():
    with SessionLocal() as db:
        return (db.scalar(select(func.count()).select_from(Account)),
                db.scalar(select(func.count()).select_from(Transaction)))


def llamar(query, variables=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        print(f"  Header enviado : Authorization: Bearer {corto(token)}")
    else:
        print("  Header enviado : (sin Authorization)")
    resp = requests.post(URL, json={"query": query,
                                    "variables": variables or {}},
                         headers=headers, timeout=15)
    return resp.json()


def login(clave):
    data = requests.post(URL, json={"query": LOGIN, "variables": {"input": {
        "email": P[clave]["correo"], "password": PASSWORD}}},
        timeout=15).json()
    if data.get("errors"):
        raise SystemExit(f"Login falló para {clave}: {data['errors']}")
    return data["data"]["login"]["token"]


def resultado(data):
    if data.get("errors"):
        return "RECHAZADO -> " + data["errors"][0]["message"]
    return "ACEPTADO  -> " + json.dumps(data["data"], ensure_ascii=False)


def conteo(antes, despues):
    print(f"  COUNT(*) antes : accounts={antes[0]} transactions={antes[1]}")
    print(f"  COUNT(*) despues: accounts={despues[0]} transactions={despues[1]}")


def cuenta_in(nombre):
    return {"input": {"companyId": str(IDS["empresa1"]["id"]),
                      "accountType": "DEBIT", "name": nombre}}


def tx_in():
    return {"input": {"accountId": str(IDS["accountId"]),
                      "conceptId": str(IDS["conceptId"]),
                      "transactionType": "INCOME", "amount": "99.90"}}


def caso(n, titulo):
    print(f"\n=== CASO {n}: {titulo} ===")


def main():
    sufijo = datetime.now().strftime("%H%M%S")

    caso(1, "Sin token + createAccount")
    a = filas()
    print("  " + resultado(llamar(CREATE_ACCOUNT, cuenta_in(f"Sin token {sufijo}"))))
    conteo(a, filas())

    caso(2, "María (CAPTURISTA) + createTransaction")
    t_maria = login("maria")
    a = filas()
    print("  " + resultado(llamar(CREATE_TX, tx_in(), t_maria)))
    conteo(a, filas())

    caso(3, "María (CAPTURISTA) + createAccount")
    a = filas()
    print("  " + resultado(llamar(CREATE_ACCOUNT, cuenta_in(f"Maria {sufijo}"), t_maria)))
    conteo(a, filas())

    caso(4, "Luis (CONTADOR) + createAccount")
    t_luis = login("luis")
    a = filas()
    print("  " + resultado(llamar(CREATE_ACCOUNT, cuenta_in(f"Luis {sufijo}"), t_luis)))
    conteo(a, filas())

    caso(5, "Pedro (CONSULTA) + createTransaction")
    t_pedro = login("pedro")
    a = filas()
    print("  " + resultado(llamar(CREATE_TX, tx_in(), t_pedro)))
    conteo(a, filas())

    caso(6, "Ana (ADMINISTRADOR) + assignRole(Pedro -> CAPTURISTA)")
    t_ana = login("ana")
    roles = llamar(ROLES, token=t_ana)["data"]["roles"]
    capturista = next(r["id"] for r in roles if r["code"] == "CAPTURISTA")
    print("  " + resultado(llamar(ASSIGN_ROLE, {"input": {
        "companyUserId": str(P["pedro"]["companyUserId"]),
        "roleId": str(capturista)}}, t_ana)))

    caso(7, "MISMO token de Pedro (sin nuevo login) + createTransaction")
    a = filas()
    print("  " + resultado(llamar(CREATE_TX, tx_in(), t_pedro)))
    conteo(a, filas())

    caso(8, "Token de la empresa 2 + accounts de la empresa 1")
    t_admin2 = login("admin2")
    print("  " + resultado(llamar(ACCOUNTS, {"companyId": str(IDS["empresa1"]["id"])},
                                  t_admin2)))

    caso(9, "Token alterado y token vencido + createAccount")
    i = len(t_luis) - 6
    alterado = t_luis[:i] + ("A" if t_luis[i] != "A" else "B") + t_luis[i + 1:]
    a = filas()
    print(" 9a) token alterado")
    print("  " + resultado(llamar(CREATE_ACCOUNT, cuenta_in(f"Alterado {sufijo}"), alterado)))
    conteo(a, filas())
    vencido = jwt.encode({
        "companyUserId": P["luis"]["companyUserId"],
        "companyId": P["luis"]["companyId"],
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
    }, JWT_SECRET, algorithm=ALGORITHM)
    a = filas()
    print(" 9b) token vencido")
    print("  " + resultado(llamar(CREATE_ACCOUNT, cuenta_in(f"Vencido {sufijo}"), vencido)))
    conteo(a, filas())

    print("\nListo. Para dejar a Pedro como CONSULTA otra vez, vuelve a "
          "ejecutar scripts/preparar_demo_actividad6.py")


if __name__ == "__main__":
    main()
