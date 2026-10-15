import time
import requests

GRAPHQL_URL = "http://127.0.0.1:8000/graphql"
PASSWORD = "Password123."


def gql_call(query: str, variables: dict | None = None) -> tuple[dict | None, str | None]:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = requests.post(GRAPHQL_URL, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        msgs = [e.get("message", str(e)) for e in data["errors"]]
        return None, "; ".join(msgs)
    return data.get("data"), None


def gql(query: str, variables: dict | None = None) -> dict:
    data, err = gql_call(query, variables)
    if err:
        raise RuntimeError(f"Error GraphQL inesperado: {err}")
    return data


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
    return gql(q, {"actor": actor_id, "input": {
        "companyUserId": company_user_id, "roleId": role_id}})


def obtener_permisos_rol(actor_id: str, role_id: str) -> list[str]:
    q = """
    query ($actor: ID!, $roleId: ID!) {
      rolePermissions(actorCompanyUserId: $actor, roleId: $roleId) {
        permission {
          code
        }
      }
    }
    """
    res = gql(q, {"actor": actor_id, "roleId": role_id})
    return sorted([item["permission"]["code"] for item in res["rolePermissions"]])


RESULTADOS: list[tuple[str, bool | None]] = []


def paso(nombre: str, esperado: str, obtenido: str, ok: bool | None) -> None:
    """Imprime 'PASO -> esperado / obtenido' y registra el resultado.
    ok=True cumplido, ok=False no cumplido, ok=None pendiente de verificar fuera de GraphQL."""
    estado = "CUMPLIDO" if ok is True else ("NO CUMPLIDO" if ok is False else "PENDIENTE")
    print(f"{nombre} -> {esperado} / {obtenido}  [{estado}]")
    RESULTADOS.append((nombre, ok))


def contar_transacciones(actor_id: str) -> int:
    q = """
    query ($actor: ID!) {
      transactions(actorCompanyUserId: $actor, limit: 100) { id }
    }
    """
    return len(gql(q, {"actor": actor_id})["transactions"])


def main():
    s = str(int(time.time()))[-6:]
    print("=" * 70)
    print(f"=== INICIANDO ACTIVIDAD 4 (Sufijo: {s}) ===")
    print("=" * 70)

    # -------------------------------------------------------------
    # SETUP: Reutilizando lógica de scripts/preparar_demo_actividad4.py
    # -------------------------------------------------------------
    # 1. Empresa
    q = """
    mutation ($input: CreateCompanyInput!) {
      createCompany(input: $input) { id }
    }
    """
    res = gql(q, {"input": {
        "name": f"Empresa Act4 {s}",
        "legalName": f"Empresa Act4 {s} S.A. de C.V.",
        "taxId": f"EA4{s}",
        "email": f"contacto_{s}@act4.com",
        "phone": "9991234567"}})
    company_id = str(res["createCompany"]["id"])

    # 2. Ana = ADMINISTRADOR
    q = """
    mutation ($input: CreateCompanyAdminInput!) {
      createCompanyAdmin(input: $input) { id }
    }
    """
    res = gql(q, {"input": {
        "companyId": company_id, "name": "Ana",
        "email": f"ana_{s}@act4.com", "password": PASSWORD}})
    ana = str(res["createCompanyAdmin"]["id"])

    # 3. Diccionarios de roles y permisos
    roles_list = gql("""query ($a: ID!) { roles(actorCompanyUserId: $a) { id code } }""",
                     {"a": ana})["roles"]
    rol = {r["code"]: str(r["id"]) for r in roles_list}

    perms_list = gql("""query ($a: ID!) { permissions(actorCompanyUserId: $a) { id code } }""",
                      {"a": ana})["permissions"]
    perm = {p["code"]: str(p["id"]) for p in perms_list}

    # 4. Luis (CONTADOR), María (CAPTURISTA), José (CAPTURISTA), Pedro (CONSULTA)
    luis = crear_usuario(ana, company_id, "Luis", f"luis_{s}@act4.com")
    maria = crear_usuario(ana, company_id, "María", f"maria_{s}@act4.com")
    jose = crear_usuario(ana, company_id, "José", f"jose_{s}@act4.com")
    pedro = crear_usuario(ana, company_id, "Pedro", f"pedro_{s}@act4.com")

    asignar_rol(ana, luis, rol["CONTADOR"])
    asignar_rol(ana, maria, rol["CAPTURISTA"])
    asignar_rol(ana, jose, rol["CAPTURISTA"])
    asignar_rol(ana, pedro, rol["CONSULTA"])

    # 5. Con Luis: cuenta, concepto y vínculo
    q = """
    mutation ($actor: ID!, $input: CreateAccountInput!) {
      createAccount(actorCompanyUserId: $actor, input: $input) { id }
    }
    """
    res = gql(q, {"actor": luis, "input": {
        "companyId": company_id, "accountType": "DEBIT",
        "name": f"Cuenta Operativa {s}", "bankName": "BBVA Bancomer",
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
        "name": f"Venta de Servicios {s}",
        "shortDescription": "Ingresos por servicios"}})
    concept_id = str(res["createConcept"]["id"])

    q = """
    mutation ($actor: ID!, $input: AssignConceptToAccountInput!) {
      assignConceptToAccount(actorCompanyUserId: $actor, input: $input) { id }
    }
    """
    gql(q, {"actor": luis, "input": {
        "accountId": account_id, "conceptId": concept_id}})

    print("[SETUP COMPLETADO]")
    print(f" Empresa: {company_id} | Ana(ADMIN): {ana} | Luis(CONTADOR): {luis}")
    print(f" María(CAPTURISTA): {maria} | José(CAPTURISTA): {jose} | Pedro(CONSULTA): {pedro}")
    print(f" Cuenta: {account_id} | Concepto: {concept_id}")
    print("=" * 70)

    # -------------------------------------------------------------
    # PARTE 1: Verificación de permisos iniciales
    # -------------------------------------------------------------
    print("\n--- PARTE 1: Verificación de permisos de roles ---")

    perms_capturista = obtener_permisos_rol(ana, rol["CAPTURISTA"])
    tiene_accounts_write = "accounts.write" in perms_capturista
    exp = "no incluye accounts.write"
    obt = "no incluye accounts.write" if not tiene_accounts_write else "incluye accounts.write"
    paso("PASO 1.1 (rolePermissions CAPTURISTA no incluye accounts.write)", exp, obt, not tiene_accounts_write)

    perms_consulta = obtener_permisos_rol(ana, rol["CONSULTA"])
    writes_consulta = [p for p in perms_consulta if ".write" in p]
    exp = "sin permisos .write"
    obt = "sin permisos .write" if len(writes_consulta) == 0 else f"tiene {writes_consulta}"
    paso("PASO 1.2 (rolePermissions CONSULTA no tiene permisos .write)", exp, obt, len(writes_consulta) == 0)

    perms_contador = obtener_permisos_rol(ana, rol["CONTADOR"])
    contador_ok = ("accounts.write" in perms_contador) and ("roles.write" not in perms_contador)
    exp = "tiene accounts.write y no roles.write"
    obt = "tiene accounts.write y no roles.write" if contador_ok else f"permisos: {perms_contador}"
    paso("PASO 1.3 (rolePermissions CONTADOR tiene accounts.write y no roles.write)", exp, obt, contador_ok)

    # -------------------------------------------------------------
    # PARTE 2: Modificación dinámica de permisos de rol y efecto en miembros
    # -------------------------------------------------------------
    print("\n--- PARTE 2: Permisos dinámicos en CAPTURISTA (createAccount) ---")

    create_acc_q = """
    mutation ($actor: ID!, $input: CreateAccountInput!) {
      createAccount(actorCompanyUserId: $actor, input: $input) { id name }
    }
    """

    # createAccount rechazado con María
    data, err = gql_call(create_acc_q, {
        "actor": maria,
        "input": {"companyId": company_id, "accountType": "DEBIT", "name": f"Cuenta María 1 {s}"}
    })
    exp = "rechazado por falta de permiso"
    obt = f"rechazado ({err})" if err else f"permitido (id: {data['createAccount']['id']})"
    paso("PASO 2.1 (createAccount con María)", exp, obt, err is not None)

    # createAccount rechazado con José
    data, err = gql_call(create_acc_q, {
        "actor": jose,
        "input": {"companyId": company_id, "accountType": "DEBIT", "name": f"Cuenta José 1 {s}"}
    })
    exp = "rechazado por falta de permiso"
    obt = f"rechazado ({err})" if err else f"permitido (id: {data['createAccount']['id']})"
    paso("PASO 2.2 (createAccount con José)", exp, obt, err is not None)

    # Ana hace assignPermissionToRole (accounts.write a CAPTURISTA)
    assign_perm_q = """
    mutation ($actor: ID!, $input: AssignPermissionToRoleInput!) {
      assignPermissionToRole(actorCompanyUserId: $actor, input: $input) {
        id
        role { code }
        permission { code }
      }
    }
    """
    data, err = gql_call(assign_perm_q, {
        "actor": ana,
        "input": {"roleId": rol["CAPTURISTA"], "permissionId": perm["accounts.write"]}
    })
    exp = "asignación exitosa"
    obt = "asignación exitosa" if (data and not err) else f"error ({err})"
    paso("PASO 2.3 (Ana assignPermissionToRole accounts.write a CAPTURISTA)", exp, obt, bool(data and not err))

    # createAccount funciona con María
    data, err = gql_call(create_acc_q, {
        "actor": maria,
        "input": {"companyId": company_id, "accountType": "DEBIT", "name": f"Cuenta María OK {s}"}
    })
    exp = "creación exitosa"
    obt = f"creación exitosa (id: {data['createAccount']['id']})" if data else f"rechazado ({err})"
    paso("PASO 2.4 (createAccount con María tras asignar permiso)", exp, obt, bool(data and not err))

    # createAccount funciona con José
    data, err = gql_call(create_acc_q, {
        "actor": jose,
        "input": {"companyId": company_id, "accountType": "DEBIT", "name": f"Cuenta José OK {s}"}
    })
    exp = "creación exitosa"
    obt = f"creación exitosa (id: {data['createAccount']['id']})" if data else f"rechazado ({err})"
    paso("PASO 2.5 (createAccount con José tras asignar permiso)", exp, obt, bool(data and not err))

    # Ana hace removePermissionFromRole
    remove_perm_q = """
    mutation ($actor: ID!, $roleId: ID!, $permissionId: ID!) {
      removePermissionFromRole(actorCompanyUserId: $actor, roleId: $roleId, permissionId: $permissionId)
    }
    """
    data, err = gql_call(remove_perm_q, {
        "actor": ana,
        "roleId": rol["CAPTURISTA"],
        "permissionId": perm["accounts.write"]
    })
    exp = "remoción exitosa"
    obt = "remoción exitosa" if (data and data.get("removePermissionFromRole")) else f"error ({err})"
    paso("PASO 2.6 (Ana removePermissionFromRole accounts.write de CAPTURISTA)", exp, obt, bool(data and data.get("removePermissionFromRole")))

    # Ambos rechazados otra vez
    data, err = gql_call(create_acc_q, {
        "actor": maria,
        "input": {"companyId": company_id, "accountType": "DEBIT", "name": f"Cuenta María 2 {s}"}
    })
    exp = "rechazado por falta de permiso"
    obt = f"rechazado ({err})" if err else f"permitido (id: {data['createAccount']['id']})"
    paso("PASO 2.7 (createAccount con María tras remover permiso)", exp, obt, err is not None)

    data, err = gql_call(create_acc_q, {
        "actor": jose,
        "input": {"companyId": company_id, "accountType": "DEBIT", "name": f"Cuenta José 2 {s}"}
    })
    exp = "rechazado por falta de permiso"
    obt = f"rechazado ({err})" if err else f"permitido (id: {data['createAccount']['id']})"
    paso("PASO 2.8 (createAccount con José tras remover permiso)", exp, obt, err is not None)

    # -------------------------------------------------------------
    # PARTE 3: Reasignación de rol a Pedro y comparación de roles
    # -------------------------------------------------------------
    print("\n--- PARTE 3: Reasignación de rol a Pedro y creación de movimiento ---")

    # Guardar rolePermissions de CONTADOR y CONSULTA antes
    perms_contador_antes = obtener_permisos_rol(ana, rol["CONTADOR"])
    perms_consulta_antes = obtener_permisos_rol(ana, rol["CONSULTA"])

    create_tx_q = """
    mutation ($actor: ID!, $input: CreateTransactionInput!) {
      createTransaction(actorCompanyUserId: $actor, input: $input) {
        id
        amount
      }
    }
    """

    # createTransaction de Pedro rechazado (está en CONSULTA) y conteo de movimientos sin cambio
    conteo_antes = contar_transacciones(ana)
    data, err = gql_call(create_tx_q, {
        "actor": pedro,
        "input": {
            "accountId": account_id,
            "conceptId": concept_id,
            "transactionType": "INCOME",
            "amount": "250.00",
            "shortDescription": "Intento de Pedro como CONSULTA"
        }
    })
    conteo_despues = contar_transacciones(ana)
    exp = "rechazado por falta de permiso y conteo de movimientos sin cambio"
    obt = (f"rechazado ({err})" if err else f"permitido (id: {data['createTransaction']['id']})") \
        + f"; movimientos antes={conteo_antes}, después={conteo_despues}"
    paso("PASO 3.1 (createTransaction de Pedro como CONSULTA)", exp, obt,
         err is not None and conteo_antes == conteo_despues)

    # Ana hace assignRole a CAPTURISTA
    assign_role_q = """
    mutation ($actor: ID!, $input: AssignRoleInput!) {
      assignRole(actorCompanyUserId: $actor, input: $input) {
        id
        role { code }
      }
    }
    """
    data, err = gql_call(assign_role_q, {
        "actor": ana,
        "input": {"companyUserId": pedro, "roleId": rol["CAPTURISTA"]}
    })
    exp = "rol CAPTURISTA asignado"
    obt = f"rol {data['assignRole']['role']['code']} asignado" if data else f"error ({err})"
    paso("PASO 3.2 (Ana assignRole CAPTURISTA a Pedro)", exp, obt,
         bool(data and data["assignRole"]["role"]["code"] == "CAPTURISTA"))

    # createTransaction de Pedro funciona
    data, err = gql_call(create_tx_q, {
        "actor": pedro,
        "input": {
            "accountId": account_id,
            "conceptId": concept_id,
            "transactionType": "INCOME",
            "amount": "250.00",
            "shortDescription": "Movimiento registrado por Pedro como CAPTURISTA"
        }
    })
    exp = "transacción creada exitosamente"
    obt = f"transacción creada exitosamente (id: {data['createTransaction']['id']}, monto: {data['createTransaction']['amount']})" if data else f"rechazado ({err})"
    paso("PASO 3.3 (createTransaction de Pedro como CAPTURISTA)", exp, obt, bool(data and not err))

    # rolePermissions de CONTADOR y CONSULTA idénticos antes y después
    perms_contador_despues = obtener_permisos_rol(ana, rol["CONTADOR"])
    perms_consulta_despues = obtener_permisos_rol(ana, rol["CONSULTA"])

    contador_identico = (perms_contador_antes == perms_contador_despues)
    exp = "rolePermissions de CONTADOR igual que antes"
    obt = "idéntico" if contador_identico else f"difiere (antes: {perms_contador_antes}, después: {perms_contador_despues})"
    paso("PASO 3.4 (rolePermissions de CONTADOR intacto)", exp, obt, contador_identico)

    consulta_identico = (perms_consulta_antes == perms_consulta_despues)
    writes_consulta_p3 = [p for p in perms_consulta_despues if ".write" in p]
    exp = "rolePermissions de CONSULTA igual que antes y sin códigos .write"
    obt = ("idéntico y sin .write" if (consulta_identico and not writes_consulta_p3)
           else f"idéntico: {consulta_identico}, códigos .write: {writes_consulta_p3}")
    paso("PASO 3.5 (rolePermissions de CONSULTA intacto y sin .write)", exp, obt,
         consulta_identico and not writes_consulta_p3)

    # GraphQL no expone una query de roles activos de la membresía (CompanyUserRole solo se
    # devuelve como resultado de assignRole), por lo que no se inventa una query.
    paso("PASO 3.6 (Pedro con un solo rol activo)", "un solo rol activo", "VERIFICAR EN MYSQL", None)

    # -------------------------------------------------------------
    # PARTE 4: Intento no autorizado de modificación de rol y gestión de Ana
    # -------------------------------------------------------------
    print("\n--- PARTE 4: Intento no autorizado y modificación por Administrador ---")

    perms_consulta_p4_antes = obtener_permisos_rol(ana, rol["CONSULTA"])

    # José intenta agregar concepts.write a CONSULTA y es rechazado
    data, err = gql_call(assign_perm_q, {
        "actor": jose,
        "input": {"roleId": rol["CONSULTA"], "permissionId": perm["concepts.write"]}
    })
    exp = "rechazado por falta de permiso roles.write"
    obt = f"rechazado ({err})" if err else f"permitido ({data})"
    paso("PASO 4.1 (José intenta agregar concepts.write a CONSULTA)", exp, obt, err is not None)

    # rolePermissions de CONSULTA igual que antes
    perms_consulta_p4_tras_jose = obtener_permisos_rol(ana, rol["CONSULTA"])
    consulta_igual_p4 = (perms_consulta_p4_antes == perms_consulta_p4_tras_jose)
    exp = "rolePermissions de CONSULTA igual que antes"
    obt = "idéntico" if consulta_igual_p4 else f"difiere ({perms_consulta_p4_antes} -> {perms_consulta_p4_tras_jose})"
    paso("PASO 4.2 (rolePermissions de CONSULTA intacto tras intento de José)", exp, obt, consulta_igual_p4)

    # Ana lo agrega
    data, err = gql_call(assign_perm_q, {
        "actor": ana,
        "input": {"roleId": rol["CONSULTA"], "permissionId": perm["concepts.write"]}
    })
    exp = "asignación exitosa por Ana"
    obt = "asignación exitosa" if data else f"error ({err})"
    paso("PASO 4.3 (Ana agrega concepts.write a CONSULTA)", exp, obt, bool(data and not err))

    # Ana luego lo quita y CONSULTA vuelve a no tener códigos .write
    data, err = gql_call(remove_perm_q, {
        "actor": ana,
        "roleId": rol["CONSULTA"],
        "permissionId": perm["concepts.write"]
    })
    perms_consulta_final = obtener_permisos_rol(ana, rol["CONSULTA"])
    writes_final = [p for p in perms_consulta_final if ".write" in p]
    removido = bool(data and data.get("removePermissionFromRole"))
    exp = "remoción exitosa por Ana y CONSULTA sin códigos .write"
    obt = (f"remoción {'exitosa' if removido else 'fallida (' + str(err) + ')'}; "
           f"códigos .write: {writes_final}")
    paso("PASO 4.4 (Ana quita concepts.write de CONSULTA)", exp, obt, removido and not writes_final)

    # -------------------------------------------------------------
    # CIERRE: Regresar a Pedro a CONSULTA con assignRole
    # -------------------------------------------------------------
    print("\n--- CIERRE: Restaurar rol de Pedro ---")
    data, err = gql_call(assign_role_q, {
        "actor": ana,
        "input": {"companyUserId": pedro, "roleId": rol["CONSULTA"]}
    })
    exp = "Pedro regresa al rol CONSULTA"
    obt = f"rol actual: {data['assignRole']['role']['code']}" if data else f"error ({err})"
    paso("PASO FINAL (Ana regresa a Pedro a CONSULTA con assignRole)", exp, obt,
         bool(data and data["assignRole"]["role"]["code"] == "CONSULTA"))

    # -------------------------------------------------------------
    # RESUMEN
    # -------------------------------------------------------------
    cumplidos = [n for n, ok in RESULTADOS if ok is True]
    no_cumplidos = [n for n, ok in RESULTADOS if ok is False]
    pendientes = [n for n, ok in RESULTADOS if ok is None]
    print("\n" + "=" * 70)
    print(f"=== RESUMEN: {len(cumplidos)} cumplidos, {len(no_cumplidos)} no cumplidos, "
          f"{len(pendientes)} pendientes de {len(RESULTADOS)} pasos ===")
    print("Cumplidos:")
    for n in cumplidos:
        print(f"  [OK] {n}")
    print("No cumplidos:")
    for n in no_cumplidos:
        print(f"  [X] {n}")
    if not no_cumplidos:
        print("  (ninguno)")
    print("Pendientes (VERIFICAR EN MYSQL):")
    for n in pendientes:
        print(f"  [?] {n}")
    print("=" * 70)


if __name__ == "__main__":
    main()
