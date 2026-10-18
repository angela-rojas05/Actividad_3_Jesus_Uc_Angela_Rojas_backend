"""Genera los archivos de variables de la Actividad 5.

Uso:
    python scripts/generar_variables_actividad5.py <id_membresia_ana>

Los ids de roles y permisos se obtienen por GraphQL; nunca se escriben a mano.
"""
import json
import sys
from pathlib import Path

import requests

URL = "http://127.0.0.1:8000/graphql"
RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "variables"

S0 = ["accounts.read", "concepts.read", "transactions.read", "transactions.write"]

Q_ROLES = """
query ListarRoles($actor: ID!) {
  roles(actorCompanyUserId: $actor) { id code isActive }
}
"""

Q_PERMISOS = """
query ListarPermisos($actor: ID!) {
  permissions(actorCompanyUserId: $actor) { id code isActive }
}
"""


def graphql(query, variables):
    resp = requests.post(
        URL, json={"query": query, "variables": variables}, timeout=30)
    resp.raise_for_status()
    cuerpo = resp.json()
    if cuerpo.get("errors"):
        raise SystemExit(f"Error GraphQL: {cuerpo['errors']}")
    return cuerpo["data"]


def escribir(nombre, datos):
    SALIDA.mkdir(exist_ok=True)
    ruta = SALIDA / f"{nombre}.json"
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"escrito: {ruta.relative_to(RAIZ)}")


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    actor = sys.argv[1]

    roles = {r["code"]: r["id"]
             for r in graphql(Q_ROLES, {"actor": actor})["roles"]}
    permisos = {p["code"]: p["id"]
                for p in graphql(Q_PERMISOS, {"actor": actor})["permissions"]}

    for codigo in ("CAPTURISTA", "ADMINISTRADOR", "CONSULTA"):
        if codigo not in roles:
            raise SystemExit(f"No existe el rol {codigo}.")
    for codigo in S0 + ["accounts.write", "concepts.write"]:
        if codigo not in permisos:
            raise SystemExit(f"No existe el permiso {codigo}.")

    ids_s0 = [permisos[c] for c in S0]
    ids_s1 = ids_s0 + [permisos["accounts.write"]]
    capturista = roles["CAPTURISTA"]

    def cfg(role_id, ids):
        return {"actor": actor, "input": {"roleId": role_id, "permissionIds": ids}}

    escribir("e01_listar", {"actor": actor})
    escribir("e01_lista_capturista", {"actor": actor, "roleId": capturista})
    escribir("e02_catalogo", {"actor": actor})
    escribir("e02_enum_invalido", {"actor": actor, "recurso": "PAYMENTS"})
    escribir("e03_e04_e05_s1", cfg(capturista, ids_s1))
    escribir("e05_e09_s0", cfg(capturista, ids_s0))
    escribir("e08_vacia", cfg(capturista, []))
    escribir("e06_rol_inexistente", cfg("99999", ids_s0))
    escribir("e06_administrador", cfg(roles["ADMINISTRADOR"], ids_s0))
    escribir("e06_permiso_inexistente", cfg(capturista, ids_s0 + ["99999"]))
    escribir("e06_permiso_repetido", cfg(capturista, ids_s0 + [ids_s0[0]]))
    escribir("e06_rol_inactivo", cfg(roles["CONSULTA"], ids_s0))
    escribir("e06_permiso_inactivo",
             cfg(capturista, ids_s0 + [permisos["concepts.write"]]))


if __name__ == "__main__":
    main()
