"""Prepara (o restaura) los datos de la Unidad III, Actividad 3 (repetible).

1. Restaura la demo de la Actividad 2 (preparar_demo_u3a2.py): Empresa A con
   Ana (ADMINISTRADOR, isAdmin), Luis (CONTADOR), María (CAPTURISTA) y Pedro
   (CONSULTA), sus cuentas y sus movimientos.
2. Deja el nombre de los diez permisos como en la tabla de la sección 2 de la
   guía ("Ver usuarios", "Crear cuentas", ...).  Solo cambia el texto del
   catálogo; no se crean roles ni permisos.
3. Restaura la matriz inicial (sección 2.2, la de la actividad 4 del
   Parcial II).  Lo que sobra se DESACTIVA; no se borra ninguna fila.
4. Agrega a José (CAPTURISTA) en la Empresa A: el segundo capturista que ve el
   mismo cambio de columna que María sin que se edite su fila en Usuarios.
5. Escribe variables/u3a3_*.json para GraphiQL.

Uso:  python scripts/preparar_demo_u3a3.py
"""
import json
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import preparar_demo_actividad7 as demo7  # noqa: E402
import preparar_demo_u3a2 as demo_u3a2  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Company,
    PermissionModel,
    RoleModel,
    RolePermissionModel,
)
from app.seed import PERMISSIONS_DATA, ROLE_PERMISSIONS_MATRIX  # noqa: E402

SALIDA = ROOT / "variables"

# El segundo capturista de la Empresa A.
JOSE = ("jose", "José", "jose@actividad7.com", "CAPTURISTA")

# Lo que la guía agrega a Capturista en la sección 4.2.
CAPTURISTA_CON_CUENTAS = [
    "accounts.read",
    "accounts.write",
    "concepts.read",
    "transactions.read",
    "transactions.write",
]


def escribir(nombre, datos):
    SALIDA.mkdir(exist_ok=True)
    ruta = SALIDA / f"{nombre}.json"
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return ruta.relative_to(ROOT)


def nombrar_permisos(db):
    """Nombre de cada permiso = columna "Nombre en la fila" de la guía."""
    por_codigo = {p["code"]: p for p in PERMISSIONS_DATA}
    for permiso in db.scalars(select(PermissionModel)).all():
        datos = por_codigo.get(permiso.code)
        if datos is None:
            continue
        permiso.name = datos["name"]
        permiso.description = datos["description"]
        permiso.is_active = True
    db.flush()


def restaurar_matriz(db):
    """Deja role_permissions como la tabla de la sección 2.2.

    Reactiva la fila que ya existía (mismo id) o la crea si nunca existió.
    Lo que no está en la tabla queda con is_active = false.
    """
    permisos = {p.code: p for p in db.scalars(select(PermissionModel)).all()}
    resumen = {}
    for codigo_rol, codigos in ROLE_PERMISSIONS_MATRIX.items():
        rol = db.scalar(select(RoleModel).where(RoleModel.code == codigo_rol))
        rol.is_active = True
        relaciones = {
            rp.permission_id: rp
            for rp in db.scalars(
                select(RolePermissionModel).where(RolePermissionModel.role_id == rol.id)
            ).all()
        }
        for codigo, permiso in permisos.items():
            deseado = codigo in codigos
            rel = relaciones.get(permiso.id)
            if rel is None and deseado:
                db.add(RolePermissionModel(role_id=rol.id, permission_id=permiso.id, is_active=True))
            elif rel is not None:
                rel.is_active = deseado
        resumen[codigo_rol] = len(codigos)
    db.flush()
    return resumen


def main():
    demo_u3a2.main()
    ids = json.loads(demo7.IDS_FILE.read_text("utf-8"))
    empresa_a_id = ids["empresas"]["A"]["id"]

    with SessionLocal() as db:
        nombrar_permisos(db)
        resumen = restaurar_matriz(db)

        empresa_a = db.get(Company, empresa_a_id)
        clave, nombre, correo, rol = JOSE
        user, cu = demo7.obtener_persona(db, empresa_a, nombre, correo, rol)
        jose = {"nombre": nombre, "correo": correo, "rol": rol,
                "userId": user.id, "companyUserId": cu.id, "companyId": empresa_a_id}

        roles = {r.code: r.id for r in db.scalars(select(RoleModel)).all()}
        permisos = {p.code: p.id for p in db.scalars(select(PermissionModel)).all()}
        db.commit()

    # ids_demo_a7.json también lleva a José, para quien lo consulte después.
    ids["personas"][clave] = jose
    demo7.IDS_FILE.write_text(json.dumps(ids, indent=2, ensure_ascii=False), encoding="utf-8")

    archivos = [
        escribir("u3a3_login_ana", {"input": {
            "email": ids["personas"]["ana"]["correo"], "password": ids["password"]}}),
        escribir("u3a3_lista_capturista", {"roleId": str(roles["CAPTURISTA"])}),
        escribir("u3a3_capturista_con_accounts_write", {"input": {
            "roleId": str(roles["CAPTURISTA"]),
            "permissionIds": [str(permisos[c]) for c in CAPTURISTA_CON_CUENTAS],
        }}),
    ]

    print("-" * 66)
    print(" UNIDAD III, ACTIVIDAD 3 - Matriz de roles y permisos")
    print(" Matriz inicial (sección 2.2) restaurada; nada se borró:")
    for codigo_rol, total in resumen.items():
        print(f"   {codigo_rol:<14} {total} permisos activos   (roleId {roles[codigo_rol]})")
    print(f" Contraseña de todos : {ids['password']}")
    print(f" {'Persona':<10}{'Rol':<15}Correo")
    for clave_p in ("ana", "luis", "maria", "jose", "pedro"):
        d = ids["personas"][clave_p]
        print(f" {d['nombre']:<10}{d['rol']:<15}{d['correo']}")
    for ruta in archivos:
        print(f" escrito: {ruta}")
    print("-" * 66)


if __name__ == "__main__":
    main()
