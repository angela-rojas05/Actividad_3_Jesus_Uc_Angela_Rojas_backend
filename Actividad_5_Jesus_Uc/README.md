# Sistema General de Ingresos — Unidad II, Actividad 6

Control de acceso según el rol con **JWT**. El cliente ya no envía `actorCompanyUserId`:
la identidad sale del token que entrega `login`, y cada ruta protegida la lee del header
`Authorization`. El rol y los permisos se consultan en la base de datos **en cada petición**
(no viajan en el token), por eso un cambio de rol surte efecto con el mismo token.

## Integrantes y aportaciones
- Jesús Omar Uc Domínguez — implementó la configuración de permisos por rol (`app/role_config.py` y `app/schema.py`), escribió las pruebas automatizadas (`tests/test_set_role_permissions.py`) y capturó las evidencias E01 a E05 (Actividad 5).
- Ángela Yaritzi Rojas Brito — preparó su propio entorno y base de datos, capturó las evidencias E06 a E10, generó la matriz final (`configuracion_final.json`), completó `evidencias.md` y redactó `investigacion.md` (Actividad 5).

## Dependencias
Python 3.12, Docker Desktop. `pip install -r requirements.txt`
(FastAPI, Strawberry, SQLAlchemy, PyMySQL, python-dotenv, PyJWT, pytest, requests).

## Configuración: JWT_SECRET
La API **no arranca** sin `JWT_SECRET` (no hay valor por defecto). Genera uno y ponlo en `.env`:
```
python -c "import secrets; print(secrets.token_hex(32))"
```
```
copy .env.example .env
# edita .env y reemplaza COLOCA_AQUI_UNA_CLAVE_SECRETA por el valor generado
```
`.env` está en `.gitignore`; nunca subas el secreto a Git.

## Iniciar API y MySQL
```
docker compose up -d
uvicorn app.main:app
```
GraphiQL: http://127.0.0.1:8000/graphql

## Datos de demo
```
python scripts/preparar_demo_actividad6.py
python scripts/generar_variables_actividad6.py
```
El primero es repetible (reutiliza datos y deja a Pedro otra vez como CONSULTA), imprime correos e IDs y
escribe `scripts/ids_demo.json` (ignorado por Git). Contraseña de todos: **`Secreto123!`**

| Empresa | Persona | Correo | Rol inicial |
|---|---|---|---|
| 1 | Ana | ana@actividad6.com | ADMINISTRADOR |
| 1 | Luis | luis@actividad6.com | CONTADOR |
| 1 | María | maria@actividad6.com | CAPTURISTA |
| 1 | Pedro | pedro@actividad6.com | CONSULTA |
| 2 | Admin Dos | admin2@actividad6.com | ADMINISTRADOR |

## Uso en GraphiQL (2 pasos)
1. Ejecuta `Login` (ver `operaciones.graphql`, variables en `variables/a6_login_<persona>.json`) y copia `token`.
   El `companyId` es opcional; solo es obligatorio si el usuario tiene membresías activas en varias empresas.
2. En la pestaña **Headers** de GraphiQL pega:
   ```json
   { "Authorization": "Bearer TOKEN" }
   ```
   y ejecuta las demás operaciones (`variables/a6_*.json`). El token dura 30 minutos.

Payload del token (sin contraseña, hash ni permisos): `{"companyUserId", "companyId", "exp"}`, firmado HS256.
Rutas públicas (sin token): `login`, `createCompany`, `createCompanyAdmin`, `companies`, `company`.

## Pruebas y scripts
```
python -m pytest -v                          # todas las pruebas
python -m pytest tests/test_control_acceso.py -v   # los 9 casos de la Actividad 6
python scripts/correr_actividad6.py          # los 9 casos contra http://127.0.0.1:8000/graphql (API levantada)
```
`correr_actividad6.py` muestra el header con el token acortado (15 caracteres + `...`) y los
`COUNT(*)` de `accounts`/`transactions` antes y después de cada escritura (también en `comprobaciones.sql`).
Tras correrlo, Pedro queda como CAPTURISTA; vuelve a ejecutar `preparar_demo_actividad6.py` para reiniciarlo.

## Matriz final (Actividad 5)
```
python scripts/generar_configuracion_final.py
```
`scripts/generar_variables_actividad5.py <TOKEN_DE_ANA>` regenera `variables/e*.json`.

## Archivos
`investigacion.md` · `operaciones.graphql` · `variables/` · `configuracion_inicial.json` · `configuracion_final.json` · `comprobaciones.sql` · `evidencias.md` · `act5_evidencias/`
