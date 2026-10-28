"""Prepara los casos B07 y B08 de la Actividad 7 y los deshace.

El proyecto no tiene una operación para desactivar cuentas, así que el estado
se prepara con este script (equivale al SQL que aparece en --sql).

    python scripts/casos_b07_b08.py b07        # desactiva el egreso de 1000.00 de Banco (28/oct)
    python scripts/casos_b07_b08.py b08        # desactiva la cuenta Banco (conserva sus movimientos)
    python scripts/casos_b07_b08.py restaurar  # vuelve al conjunto inicial (activos todos)

Después de b07 o b08, consulta en GraphiQL y compara con evidencias.  Para
repetir el caso o pasar al siguiente, ejecuta primero `restaurar`.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import importlib.util  # noqa: E402

from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.financial_models import Account, Transaction  # noqa: E402

IDS = json.loads((ROOT / "scripts" / "ids_demo_a7.json").read_text("utf-8"))


def desactivar_movimiento():
    with SessionLocal() as db:
        tx = db.scalar(select(Transaction).where(
            Transaction.account_id == IDS["cuentas"]["banco"],
            Transaction.short_description == "Compra de materiales"))
        tx.is_active = False
        db.commit()
        print(f"Movimiento {tx.id} (Banco, 28/oct, EXPENSE 1000.00) desactivado.")
        print("Esperado Banco 26-30: ingresos 3000.00, egresos 1200.00, "
              "profit 1800.00, saldo final 2800.00.")
        print("Los demás movimientos siguen en la tabla: "
              "SELECT id, is_active FROM transactions WHERE account_id = "
              f"{IDS['cuentas']['banco']};")


def desactivar_cuenta():
    with SessionLocal() as db:
        cuenta = db.get(Account, IDS["cuentas"]["banco"])
        cuenta.is_active = False
        db.commit()
        print(f"Cuenta {cuenta.id} (Banco) desactivada.")
        print("Esperado: Banco sigue en el balance con isActive false y "
              "conserva su aportación (saldo final 1800.00); el general no cambia.")


def restaurar():
    ruta = ROOT / "scripts" / "preparar_demo_actividad7.py"
    spec = importlib.util.spec_from_file_location("preparar_a7", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    modulo.main()


ACCIONES = {
    "b07": desactivar_movimiento,
    "b08": desactivar_cuenta,
    "restaurar": restaurar,
}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ACCIONES:
        sys.exit(__doc__)
    ACCIONES[sys.argv[1]]()
