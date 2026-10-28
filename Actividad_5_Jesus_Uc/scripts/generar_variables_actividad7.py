"""Genera variables/a7_*.json para GraphiQL (Actividad 7).

Lee scripts/ids_demo_a7.json (creado por preparar_demo_actividad7.py).  Los
archivos NO contienen tokens: el token se obtiene con `login` y se pega en el
header Authorization.

Uso:  python scripts/generar_variables_actividad7.py
"""
import json
import sys
from pathlib import Path

from sqlalchemy import select

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    PermissionModel,
    RoleModel,
    RolePermissionModel,
)

SALIDA = RAIZ / "variables"
IDS = json.loads((RAIZ / "scripts" / "ids_demo_a7.json").read_text("utf-8"))

PERIODO = {"from": "2026-10-26", "to": "2026-10-30"}


def escribir(nombre, datos):
    SALIDA.mkdir(exist_ok=True)
    ruta = SALIDA / f"{nombre}.json"
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"escrito: {ruta.relative_to(RAIZ)}")


def movimiento(cuenta, concepto, tipo, monto, fecha=None):
    datos = {"accountId": str(cuenta), "conceptId": str(concepto),
             "transactionType": tipo, "amount": monto}
    if fecha:
        datos["transactionDate"] = fecha
    return {"input": datos}


def main():
    c, k, p = IDS["cuentas"], IDS["conceptos"], IDS["personas"]

    for clave, persona in p.items():
        escribir(f"a7_login_{clave}", {"input": {
            "email": persona["correo"], "password": IDS["password"]}})

    # B01 / B02: balances de la empresa A
    for nombre in ("banco", "caja", "ahorro"):
        escribir(f"a7_balance_{nombre}",
                 {"accountId": str(c[nombre]), **PERIODO})
    escribir("a7_balance_banco_dia28", {
        "accountId": str(c["banco"]), "from": "2026-10-28", "to": "2026-10-28"})
    escribir("a7_balance_general", PERIODO)

    # B10: fechas invertidas
    escribir("a7_b10_fechas_invertidas", {
        "accountId": str(c["banco"]), "from": "2026-10-30", "to": "2026-10-26"})

    # B12: Ana (empresa A) pide la cuenta de la empresa B
    escribir("a7_b12_cuenta_ajena", {
        "accountId": str(c["pruebaB"]), **PERIODO})

    # B04: movimientos en los bordes (Admin B, Cuenta Prueba B)
    escribir("a7_balance_cuenta_b", {"accountId": str(c["pruebaB"]), **PERIODO})
    for nombre, tipo, concepto, monto, fecha in [
        ("b04_antes_inicio", "INCOME", k["ingresoB"], "1.00", "2026-10-25T23:59:59Z"),
        ("b04_inicio", "INCOME", k["ingresoB"], "10.00", "2026-10-26T00:00:00Z"),
        ("b04_fin_dia30", "EXPENSE", k["egresoB"], "4.00", "2026-10-30T23:59:59Z"),
        ("b04_medianoche_31", "INCOME", k["ingresoB"], "100.00", "2026-10-31T00:00:00Z"),
    ]:
        escribir(f"a7_{nombre}", movimiento(c["pruebaB"], concepto, tipo, monto, fecha))

    # B05: movimiento del 27 capturado después
    escribir("a7_b05_captura_posterior", movimiento(
        c["pruebaB"], k["egresoB"], "EXPENSE", "75.00", "2026-10-27T12:00:00Z"))

    # B06: centavos exactos
    escribir("a7_b06_ingreso_010", movimiento(
        c["pruebaB"], k["ingresoB"], "INCOME", "0.10", "2026-10-27T12:00:00Z"))
    escribir("a7_b06_ingreso_020", movimiento(
        c["pruebaB"], k["ingresoB"], "INCOME", "0.20", "2026-10-27T12:00:00Z"))
    escribir("a7_b06_egreso_030", movimiento(
        c["pruebaB"], k["egresoB"], "EXPENSE", "0.30", "2026-10-27T12:00:00Z"))

    # B09: otro concepto permitido para Banco (sin movimientos nuevos)
    escribir("a7_b09_asignar_concepto", {"input": {
        "accountId": str(c["banco"]), "conceptId": str(k["extraA"])}})

    # B13: Pedro (CONSULTA) intenta capturar
    escribir("a7_b13_captura_consulta", movimiento(
        c["banco"], k["ingresoA"], "INCOME", "10.00"))

    # B14: quitar transactions.read al rol CONSULTA (Ana, ADMINISTRADOR) y
    # restaurar.  Se parte de los permisos activos del rol en este momento.
    with SessionLocal() as db:
        rol = db.scalar(select(RoleModel).where(RoleModel.code == "CONSULTA"))
        activos = db.execute(
            select(PermissionModel.id, PermissionModel.code)
            .join(RolePermissionModel,
                  RolePermissionModel.permission_id == PermissionModel.id)
            .where(RolePermissionModel.role_id == rol.id,
                   RolePermissionModel.is_active.is_(True),
                   PermissionModel.is_active.is_(True))
            .order_by(PermissionModel.id)).all()
    completos = [str(i) for i, _ in activos]
    sin_lectura = [str(i) for i, codigo in activos
                   if codigo != "transactions.read"]
    escribir("a7_b14_quitar_transactions_read", {"input": {
        "roleId": str(rol.id), "permissionIds": sin_lectura}})
    escribir("a7_b14_restaurar_permisos", {"input": {
        "roleId": str(rol.id), "permissionIds": completos}})

    # B15: egreso de 50.00 en cuenta vacía
    escribir("a7_b15_egreso_50", movimiento(
        c["pruebaB"], k["egresoB"], "EXPENSE", "50.00", "2026-10-27T12:00:00Z"))


if __name__ == "__main__":
    main()
