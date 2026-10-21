"""Genera variables/a6_*.json para GraphiQL (Actividad 6).

Lee scripts/ids_demo.json (creado por preparar_demo_actividad6.py) y el id
del rol CAPTURISTA desde la base de datos.  Los archivos NO contienen tokens:
el token se obtiene con `login` y se pega en el header Authorization.

Uso:  python scripts/generar_variables_actividad6.py
"""
import json
import sys
from pathlib import Path

from sqlalchemy import select

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from app.database import SessionLocal  # noqa: E402
from app.models import RoleModel  # noqa: E402

SALIDA = RAIZ / "variables"
IDS = json.loads((RAIZ / "scripts" / "ids_demo.json").read_text("utf-8"))


def escribir(nombre, datos):
    SALIDA.mkdir(exist_ok=True)
    ruta = SALIDA / f"{nombre}.json"
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"escrito: {ruta.relative_to(RAIZ)}")


def main():
    with SessionLocal() as db:
        capturista = db.scalar(
            select(RoleModel.id).where(RoleModel.code == "CAPTURISTA"))

    for clave, p in IDS["personas"].items():
        escribir(f"a6_login_{clave}", {"input": {
            "email": p["correo"], "password": IDS["password"]}})

    empresa1 = str(IDS["empresa1"]["id"])
    escribir("a6_create_account", {"input": {
        "companyId": empresa1, "accountType": "DEBIT",
        "name": "Cuenta de prueba GraphiQL"}})
    escribir("a6_create_transaction", {"input": {
        "accountId": str(IDS["accountId"]),
        "conceptId": str(IDS["conceptId"]),
        "transactionType": "INCOME", "amount": "100.00"}})
    escribir("a6_assign_role_pedro_capturista", {"input": {
        "companyUserId": str(IDS["personas"]["pedro"]["companyUserId"]),
        "roleId": str(capturista)}})
    escribir("a6_accounts_empresa1", {"companyId": empresa1})


if __name__ == "__main__":
    main()
