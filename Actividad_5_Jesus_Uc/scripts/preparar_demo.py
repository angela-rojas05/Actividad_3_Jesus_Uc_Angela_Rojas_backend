import json
import time
from pathlib import Path
import requests

GRAPHQL_URL = "http://127.0.0.1:8000/graphql"


def graphql_request(query: str, variables: dict | None = None) -> dict:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    response = requests.post(GRAPHQL_URL, json=payload, headers={"Content-Type": "application/json"})
    response.raise_for_status()
    data = response.json()

    if "errors" in data and data["errors"]:
        error_msgs = [e.get("message", str(e)) for e in data["errors"]]
        raise RuntimeError(f"GraphQL Errors: {', '.join(error_msgs)}")

    return data.get("data", {})


def main():
    suffix = str(int(time.time()))[-6:]
    tax_id = f"EDR{suffix}"
    admin_email = f"admin_{suffix}@demoroles.com"
    contador_email = f"contador_{suffix}@demoroles.com"
    capturista_email = f"capturista_{suffix}@demoroles.com"
    consulta_email = f"consulta_{suffix}@demoroles.com"
    segundo_admin_email = f"admin2_{suffix}@demoroles.com"

    print(f"=== INICIANDO PREPARACIÓN DE DEMO (Sufijo: {suffix}) ===")

    # 1. Crear Empresa nueva
    create_company_mutation = """
    mutation ($input: CreateCompanyInput!) {
      createCompany(input: $input) {
        id
        name
        taxId
      }
    }
    """
    company_input = {
        "name": f"Empresa Demo Roles {suffix}",
        "legalName": f"Empresa Demo Roles {suffix} S.A. de C.V.",
        "taxId": tax_id,
        "email": f"contacto_{suffix}@demoroles.com",
        "phone": "9991234567"
    }
    res_company = graphql_request(create_company_mutation, {"input": company_input})
    company_id = str(res_company["createCompany"]["id"])
    print(f"[OK] Empresa creada: ID = {company_id}, taxId = {tax_id}")

    # 2. Crear Administrador Principal (Recibe rol ADMINISTRADOR automático)
    create_admin_mutation = """
    mutation ($input: CreateCompanyAdminInput!) {
      createCompanyAdmin(input: $input) {
        id
        companyId
        userId
        isAdmin
        isActive
      }
    }
    """
    admin_input = {
        "companyId": company_id,
        "name": "Admin Principal",
        "email": admin_email,
        "password": "Password123."
    }
    res_admin = graphql_request(create_admin_mutation, {"input": admin_input})
    admin_company_user_id = str(res_admin["createCompanyAdmin"]["id"])
    print(f"[OK] Admin principal creado: CompanyUserId = {admin_company_user_id}, Email = {admin_email}")

    # 3. Consultar Roles usando admin_company_user_id
    roles_query = """
    query ($actorCompanyUserId: ID!) {
      roles(actorCompanyUserId: $actorCompanyUserId) {
        id
        code
        name
      }
    }
    """
    res_roles = graphql_request(roles_query, {"actorCompanyUserId": admin_company_user_id})
    roles_map = {r["code"]: str(r["id"]) for r in res_roles["roles"]}
    print("[OK] Roles obtenidos del sistema:")
    for code, r_id in roles_map.items():
        print(f"     - {code}: ID = {r_id}")

    role_admin_id = roles_map["ADMINISTRADOR"]
    role_contador_id = roles_map["CONTADOR"]
    role_capturista_id = roles_map["CAPTURISTA"]
    role_consulta_id = roles_map["CONSULTA"]

    # 4. Con el Admin como actor, crear tres usuarios: Contador, Capturista, Consulta
    create_user_mutation = """
    mutation ($actorCompanyUserId: ID!, $input: CreateCompanyUserInput!) {
      createCompanyUser(actorCompanyUserId: $actorCompanyUserId, input: $input) {
        id
        userId
        isAdmin
      }
    }
    """

    res_cu_contador = graphql_request(create_user_mutation, {
        "actorCompanyUserId": admin_company_user_id,
        "input": {
            "companyId": company_id,
            "name": "Carlos Contador",
            "email": contador_email,
            "password": "Password123."
        }
    })
    contador_company_user_id = str(res_cu_contador["createCompanyUser"]["id"])

    res_cu_capturista = graphql_request(create_user_mutation, {
        "actorCompanyUserId": admin_company_user_id,
        "input": {
            "companyId": company_id,
            "name": "Camilo Capturista",
            "email": capturista_email,
            "password": "Password123."
        }
    })
    capturista_company_user_id = str(res_cu_capturista["createCompanyUser"]["id"])

    res_cu_consulta = graphql_request(create_user_mutation, {
        "actorCompanyUserId": admin_company_user_id,
        "input": {
            "companyId": company_id,
            "name": "Claudia Consulta",
            "email": consulta_email,
            "password": "Password123."
        }
    })
    consulta_company_user_id = str(res_cu_consulta["createCompanyUser"]["id"])

    print(f"[OK] Usuarios creados: Contador={contador_company_user_id}, Capturista={capturista_company_user_id}, Consulta={consulta_company_user_id}")

    # 5. Asignar roles explícitos
    assign_role_mutation = """
    mutation ($actorCompanyUserId: ID!, $input: AssignRoleInput!) {
      assignRole(actorCompanyUserId: $actorCompanyUserId, input: $input) {
        id
        role {
          code
        }
      }
    }
    """
    graphql_request(assign_role_mutation, {
        "actorCompanyUserId": admin_company_user_id,
        "input": {"companyUserId": contador_company_user_id, "roleId": role_contador_id}
    })
    graphql_request(assign_role_mutation, {
        "actorCompanyUserId": admin_company_user_id,
        "input": {"companyUserId": capturista_company_user_id, "roleId": role_capturista_id}
    })
    graphql_request(assign_role_mutation, {
        "actorCompanyUserId": admin_company_user_id,
        "input": {"companyUserId": consulta_company_user_id, "roleId": role_consulta_id}
    })
    print("[OK] Roles asignados exitosamente a cada miembro.")

    # 6. Con el Contador: crear Cuenta, crear Concepto (INCOME) y vincularlos
    create_account_mutation = """
    mutation ($actorCompanyUserId: ID!, $input: CreateAccountInput!) {
      createAccount(actorCompanyUserId: $actorCompanyUserId, input: $input) {
        id
        name
        accountType
      }
    }
    """
    res_account = graphql_request(create_account_mutation, {
        "actorCompanyUserId": contador_company_user_id,
        "input": {
            "companyId": company_id,
            "accountType": "DEBIT",
            "name": "Cuenta Operativa BBVA",
            "bankName": "BBVA Bancomer",
            "accountNumber": "0123456789",
            "shortDescription": "Cuenta bancaria para operaciones"
        }
    })
    account_id = str(res_account["createAccount"]["id"])
    print(f"[OK] Cuenta creada por Contador: ID = {account_id}")

    create_concept_mutation = """
    mutation ($actorCompanyUserId: ID!, $input: CreateConceptInput!) {
      createConcept(actorCompanyUserId: $actorCompanyUserId, input: $input) {
        id
        name
        conceptType
      }
    }
    """
    res_concept = graphql_request(create_concept_mutation, {
        "actorCompanyUserId": contador_company_user_id,
        "input": {
            "companyId": company_id,
            "conceptType": "INCOME",
            "name": "Venta de Servicios",
            "shortDescription": "Ingresos por servicios profesionales"
        }
    })
    concept_id = str(res_concept["createConcept"]["id"])
    print(f"[OK] Concepto creado por Contador: ID = {concept_id}")

    assign_concept_mutation = """
    mutation ($actorCompanyUserId: ID!, $input: AssignConceptToAccountInput!) {
      assignConceptToAccount(actorCompanyUserId: $actorCompanyUserId, input: $input) {
        id
        account { name }
        concept { name }
      }
    }
    """
    graphql_request(assign_concept_mutation, {
        "actorCompanyUserId": contador_company_user_id,
        "input": {
            "accountId": account_id,
            "conceptId": concept_id
        }
    })
    print(f"[OK] Concepto {concept_id} vinculado a Cuenta {account_id} por Contador.")

    # 7. Estructurar y guardar datos en scripts/ids_demo.json
    ids_data = {
        "COMPANY_ID": company_id,
        "COMPANY_NAME": f"Empresa Demo Roles {suffix}",
        "TAX_ID": tax_id,
        "ADMIN_COMPANY_USER_ID": admin_company_user_id,
        "ADMIN_EMAIL": admin_email,
        "CONTADOR_COMPANY_USER_ID": contador_company_user_id,
        "CONTADOR_EMAIL": contador_email,
        "CAPTURISTA_COMPANY_USER_ID": capturista_company_user_id,
        "CAPTURISTA_EMAIL": capturista_email,
        "CONSULTA_COMPANY_USER_ID": consulta_company_user_id,
        "CONSULTA_EMAIL": consulta_email,
        "SEGUNDO_ADMIN_EMAIL": segundo_admin_email,
        "ACCOUNT_ID": account_id,
        "CONCEPT_ID": concept_id,
        "ROLE_ID_ADMINISTRADOR": role_admin_id,
        "ROLE_ID_CONTADOR": role_contador_id,
        "ROLE_ID_CAPTURISTA": role_capturista_id,
        "ROLE_ID_CONSULTA": role_consulta_id,
    }

    out_file = Path("scripts/ids_demo.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(ids_data, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Identificadores guardados en {out_file.resolve()}\n")

    # 8. Imprimir tabla de IDs
    print("=" * 65)
    print("           TABLA DE IDENTIFICADORES GENERADOS")
    print("=" * 65)
    for key, val in ids_data.items():
        print(f" {key:<28} : {val}")
    print("=" * 65)


if __name__ == "__main__":
    main()
