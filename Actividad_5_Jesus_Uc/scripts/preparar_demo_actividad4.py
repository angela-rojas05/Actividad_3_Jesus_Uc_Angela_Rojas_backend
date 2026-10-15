import time
import requests

GRAPHQL_URL = "http://127.0.0.1:8000/graphql"
PASSWORD = "Password123."


def gql(query: str, variables: dict | None = None) -> dict:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = requests.post(GRAPHQL_URL, json=payload)
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        msgs = [e.get("message", str(e)) for e in data["errors"]]
        raise RuntimeError("GraphQL Errors: " + ", ".join(msgs))
    return data["data"]


def crear_usuario(actor_id, company_id, nombre, email):
    q = """
    mutation ($actor: ID!, $input: CreateCompanyUserInput!) {
      createCompanyUser(actorCompanyUserId: $actor, input: $input) { id }
    }
    """
    res = gql(q, {"actor": actor_id, "input": {
        "companyId": company_id, "name": nombre,
        "email": email, "password": PASSWORD}})
    return str(res["createCompanyUser"]["id"])


def asignar_rol(actor_id, company_user_id, role_id):
    q = """
    mutation ($actor: ID!, $input: AssignRoleInput!) {
      assignRole(actorCompanyUserId: $actor, input: $input) { id role { code } }
    }
    """
    gql(q, {"actor": actor_id, "input": {
        "companyUserId": company_user_id, "roleId": role_id}})


def main():
    s = str(int(time.time()))[-6:]
    print(f"=== PREPARANDO ACTIVIDAD 4 (sufijo {s}) ===")

    # 1. Empresa
    q = """
    mutation ($input: CreateCompanyInput!) {
      createCompany(input: $input) { id }
    }
    """
    res = gql(q, {"input": {
        "name": f"Empresa Permisos {s}",
        "legalName": f"Empresa Permisos {s} S.A. de C.V.",
        "taxId": f"EPA{s}",
        "email": f"contacto_{s}@permisos.com",
        "phone": "9991234567"}})
    company_id = str(res["createCompany"]["id"])
    print(f"[OK] Empresa creada: {company_id}")

    # 2. Ana = administrador principal (rol ADMINISTRADOR automatico)
    q = """
    mutation ($input: CreateCompanyAdminInput!) {
      createCompanyAdmin(input: $input) { id }
    }
    """
    res = gql(q, {"input": {
        "companyId": company_id, "name": "Ana",
        "email": f"ana_{s}@permisos.com", "password": PASSWORD}})
    ana = str(res["createCompanyAdmin"]["id"])
    print(f"[OK] Ana (ADMINISTRADOR): {ana}")

    # 3. IDs de roles y permisos
    roles = gql("""query ($a: ID!) { roles(actorCompanyUserId: $a) { id code } }""",
                {"a": ana})["roles"]
    rol = {r["code"]: str(r["id"]) for r in roles}
    perms = gql("""query ($a: ID!) { permissions(actorCompanyUserId: $a) { id code } }""",
                {"a": ana})["permissions"]
    perm = {p["code"]: str(p["id"]) for p in perms}

    # 4. Luis, Maria, Jose, Pedro
    luis = crear_usuario(ana, company_id, "Luis", f"luis_{s}@permisos.com")
    maria = crear_usuario(ana, company_id, "María", f"maria_{s}@permisos.com")
    jose = crear_usuario(ana, company_id, "José", f"jose_{s}@permisos.com")
    pedro = crear_usuario(ana, company_id, "Pedro", f"pedro_{s}@permisos.com")

    asignar_rol(ana, luis, rol["CONTADOR"])
    asignar_rol(ana, maria, rol["CAPTURISTA"])
    asignar_rol(ana, jose, rol["CAPTURISTA"])
    asignar_rol(ana, pedro, rol["CONSULTA"])
    print("[OK] Roles: Luis=CONTADOR, María=CAPTURISTA, José=CAPTURISTA, Pedro=CONSULTA")

    # 5. Con Luis: una cuenta, un concepto y su vinculo (para poder registrar movimientos)
    q = """
    mutation ($actor: ID!, $input: CreateAccountInput!) {
      createAccount(actorCompanyUserId: $actor, input: $input) { id }
    }
    """
    res = gql(q, {"actor": luis, "input": {
        "companyId": company_id, "accountType": "DEBIT",
        "name": "Cuenta Operativa", "bankName": "BBVA Bancomer",
        "accountNumber": "0123456789",
        "shortDescription": "Cuenta base de la empresa"}})
    account_id = str(res["createAccount"]["id"])

    q = """
    mutation ($actor: ID!, $input: CreateConceptInput!) {
      createConcept(actorCompanyUserId: $actor, input: $input) { id }
    }
    """
    res = gql(q, {"actor": luis, "input": {
        "companyId": company_id, "conceptType": "INCOME",
        "name": "Venta de Servicios",
        "shortDescription": "Ingresos por servicios"}})
    concept_id = str(res["createConcept"]["id"])

    q = """
    mutation ($actor: ID!, $input: AssignConceptToAccountInput!) {
      assignConceptToAccount(actorCompanyUserId: $actor, input: $input) { id }
    }
    """
    gql(q, {"actor": luis, "input": {
        "accountId": account_id, "conceptId": concept_id}})
    print(f"[OK] Cuenta {account_id} y concepto {concept_id} creados por Luis")

    filas = [
        ("COMPANY_ID", company_id),
        ("ANA (ADMINISTRADOR)", ana),
        ("LUIS (CONTADOR)", luis),
        ("MARIA (CAPTURISTA)", maria),
        ("JOSE (CAPTURISTA)", jose),
        ("PEDRO (CONSULTA)", pedro),
        ("ACCOUNT_ID", account_id),
        ("CONCEPT_ID", concept_id),
        ("ROL ADMINISTRADOR", rol["ADMINISTRADOR"]),
        ("ROL CONTADOR", rol["CONTADOR"]),
        ("ROL CAPTURISTA", rol["CAPTURISTA"]),
        ("ROL CONSULTA", rol["CONSULTA"]),
        ("PERMISO accounts.write", perm["accounts.write"]),
        ("PERMISO concepts.write", perm["concepts.write"]),
    ]
    print("\n" + "=" * 50)
    print("        TABLA DE IDENTIFICADORES")
    print("=" * 50)
    for nombre, valor in filas:
        print(f" {nombre:<26}: {valor}")
    print("=" * 50)


if __name__ == "__main__":
    main()