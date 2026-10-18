"""Escribe configuracion_final.json con las concesiones ACTIVAS de cada rol (por códigos).

Uso (desde la raíz del proyecto, con MySQL encendido): python scripts/generar_configuracion_final.py
Compara el resultado con configuracion_inicial.json e imprime si son idénticos.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import PermissionModel, RoleModel, RolePermissionModel  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def main():
    with SessionLocal() as db:
        final = {}
        for rol in db.scalars(select(RoleModel).order_by(RoleModel.code)):
            codigos = db.scalars(
                select(PermissionModel.code)
                .join(RolePermissionModel, RolePermissionModel.permission_id == PermissionModel.id)
                .where(RolePermissionModel.role_id == rol.id, RolePermissionModel.is_active.is_(True))
                .order_by(PermissionModel.code)
            ).all()
            final[rol.code] = list(codigos)
    (RAIZ / "configuracion_final.json").write_text(
        json.dumps(final, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    inicial = json.loads((RAIZ / "configuracion_inicial.json").read_text(encoding="utf-8"))
    normal = lambda d: {k: sorted(v) for k, v in d.items()}  # noqa: E731
    print("configuracion_final.json escrito.")
    print("IDÉNTICA a configuracion_inicial.json" if normal(final) == normal(inicial)
          else "DIFERENTE de configuracion_inicial.json: revisa qué rol cambió")
    for rol, lista in final.items():
        print(f"  {rol}: {len(lista)} permisos activos")


if __name__ == "__main__":
    main()
