# Sistema General de Ingresos — Unidad III, Actividad 2

**Integrantes:** Jesús Omar Uc Domínguez · Ángela Yaritzi Rojas Brito

## Unidad III, Actividad 2: idempotencia y dashboard administrativo
Detalle del cliente y de cómo se entra a la administración: `../dashboard/README.md`.

```
docker compose up -d                          # MySQL (puerto 3307)
python scripts/preparar_demo_u3a2.py          # datos de la demo + variables u3a2_*.json
uvicorn app.main:app                          # API (puerto 8000)
```

**Parte 1, idempotencia en `createTransaction`:**
- `CreateTransactionInput` acepta `idempotencyKey` (opcional, 8 a 100 caracteres). El cliente la genera
  una vez por acción y la repite en cada reintento. Sin llave, cada envío es un movimiento nuevo, como antes.
- Tabla nueva `idempotency_keys` (`app/financial_models.py`, modelo `IdempotencyKey`): índice único
  `(company_id, operation, idempotency_key)`, hash SHA-256 del cuerpo normalizado y el id del movimiento.
  `create_all` la crea al arrancar; no se modificó ninguna tabla existente.
- El resolver busca la llave; si ya existe con el mismo cuerpo, devuelve el mismo movimiento sin otro
  `INSERT`. Si es nueva, inserta el movimiento y la llave en la misma sesión y hace **un solo `COMMIT`**.
  Si dos peticiones llegan a la vez, el índice único rechaza la segunda, se hace `rollback` (su
  movimiento no queda) y se devuelve el que ya se guardó.
- La misma llave con otro monto, cuenta o concepto se rechaza: `Esa idempotencyKey ya se usó con otros datos.`
- La llave es por empresa: la misma cadena en otra empresa es otra llave.

**Parte 2, API para el dashboard administrativo** (`app/schema.py`):
- `CompanyUser.role { id code name }`: el rol activo que ya guarda `company_user_roles` (null si no tiene).
- Consulta `myAccess`: empresa, membresía, rol y permisos del token, leídos de la BD. El dashboard la usa
  para saber qué botones de alta dibujar; el servidor sigue validando cada permiso en cada mutación.
- El resto ya existía: `companyUsers`, `accounts`, `concepts`, `accountConcepts`, `createCompanyUser`,
  `deactivateCompanyUser`, `createAccount`, `createConcept`, `assignConceptToAccount` y
  `removeConceptFromAccount`.

Pruebas: `tests/test_unidad3_actividad2.py` (14 casos, incluido el de cinco reintentos simultáneos con la
misma llave). Comprobaciones SQL: `comprobaciones_u3a2.sql`. Operaciones de GraphiQL: al final de
`operaciones.graphql`.

## Unidad III, Actividad 1: dashboard financiero
Cliente web (HTML + CSS + JavaScript) en la carpeta `dashboard/` de la raíz del repositorio. Inicia
sesión con la mutación `login`, pide el período y pinta los indicadores de `generalBalance` con
`Authorization: Bearer`. Detalle, boceto, evidencias y guion de la demo: `../dashboard/README.md`.

```
docker compose up -d                          # MySQL (puerto 3307)
python scripts/preparar_demo_actividad7.py    # datos de demostración
uvicorn app.main:app                          # API (puerto 8000)
```
- Dashboard: http://127.0.0.1:8000/dashboard/ (lo sirve el mismo API, no hay otro proceso)
- GraphiQL: http://127.0.0.1:8000/graphql
- Usuario de prueba: `ana@actividad7.com` / `Secreto123!` · Período de demostración: 2026-10-26 a 2026-10-30

Cambios en el backend para esta actividad (`app/main.py`): se sirve `dashboard/` en `/dashboard/`
(mismo origen) y se agregó CORS de desarrollo para `localhost`/`127.0.0.1` en los puertos 5173 y 5500
(configurable con `CORS_ORIGINS` en `.env`). No cambiaron el esquema GraphQL ni las tablas.

## Unidad II, Actividad 7

**Actividad 7:** balances por cuenta (`accountBalance`) y balance general (`generalBalance`),
calculados en MySQL a partir de los movimientos (no se guardan). Parte de la Actividad 6, cuyo
control de acceso con **JWT** se conserva: el cliente no envía `actorCompanyUserId`, la identidad sale
del token que entrega `login` (header `Authorization`), y el rol y los permisos se consultan en la
base de datos **en cada petición** (no viajan en el token).

## Qué se agregó en la Actividad 7
- `app/balances.py` — servicio de cálculo: una consulta agregada (`SUM` + `CASE`, `LEFT JOIN` desde las cuentas, filtros del movimiento en el `ON`). Importes en `Decimal`, resultados vacíos en `0.00`.
- `app/schema.py` — tipos `AccountBalance` y `GeneralBalance`, consultas `accountBalance(accountId, fromDate, toDate)` y `generalBalance(fromDate, toDate)`; `Transaction` ya expone `transactionDate` y `capturedAt`; `createTransaction` acepta `transactionDate` opcional, lo normaliza a **UTC** y rechaza montos no positivos, no finitos o con más de 2 decimales.
- El escalar de fecha y hora se llama ahora `DateTime` (antes `Time`) y se devuelve con `Z`: **todas las fechas y horas son UTC**; un valor sin zona se toma como UTC. Las filas previas ya estaban en UTC.
- Reglas: periodo en días completos UTC (`transaction_date >= fromDate 00:00Z` y `< toDate + 1 día`), saldo inicial = movimientos anteriores al inicio, `profit = ingresos − egresos`, `isInRed = saldo final < 0`, moneda `MXN`. Se usa siempre `transaction_date`, nunca `captured_at`.
- Ambas consultas exigen `accounts.read` y `transactions.read` y filtran por la empresa del token. Una cuenta ajena e inexistente responden lo mismo (`Cuenta no disponible.`).
- No se agregaron índices ni se cambió ninguna tabla, por lo que no hay migración.

## Integrantes y aportaciones
- Jesús Omar Uc Domínguez — implementó el cálculo de balances (`app/balances.py`) y las consultas `accountBalance` y `generalBalance` con sus tipos en `app/schema.py`, la fecha de operación en UTC y la validación de montos; ejecutó en GraphiQL los casos B01 a B03 y B09 a B13 y capturó sus evidencias.
- Ángela Yaritzi Rojas Brito — preparó el conjunto de datos y los scripts de restauración (`scripts/preparar_demo_actividad7.py`, `scripts/casos_b07_b08.py`), escribió las pruebas automatizadas (`tests/test_balances.py`), generó las variables y `operaciones.graphql`, y capturó las evidencias de los casos B04 a B08, B14 y B15 y de `pytest`.
- Ambos revisaron la lista de verificación de la guía y redactaron `Evidencias act7.md` y la explicación de Banco y Caja.

Aportaciones de actividades anteriores:
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

## Datos de la Actividad 7 (preparar y restaurar)
```
python scripts/preparar_demo_actividad7.py
python scripts/generar_variables_actividad7.py
```
El primero es repetible y **restaura** el estado inicial (vuelve a crear los movimientos de la guía y
reactiva cuentas); imprime los IDs y escribe `scripts/ids_demo_a7.json` (ignorado por Git). El segundo
genera `variables/a7_*.json` (sin tokens). Contraseña de todos: **`Secreto123!`**

| Empresa | Persona | Correo | Rol |
|---|---|---|---|
| A (referencia) | Ana | ana@actividad7.com | ADMINISTRADOR |
| A | Luis | luis@actividad7.com | CONTADOR |
| A | María | maria@actividad7.com | CAPTURISTA |
| A | Pedro | pedro@actividad7.com | CONSULTA |
| B (laboratorio) | Admin B | adminb@actividad7.com | ADMINISTRADOR |
| C (sin cuentas) | Admin C | adminc@actividad7.com | ADMINISTRADOR |

- **Empresa A:** cuentas Banco, Caja y Ahorro con los 6 movimientos de la guía (a las 12:00:00Z). Es el conjunto de B01, B02, B07, B08, B09, B12 (como Ana), B13 y B14.
- **Empresa B:** `Cuenta Prueba B`, vacía, para los casos que capturan movimientos (B04, B05, B06, B15) y como cuenta ajena en B12. Entre un caso y otro ejecuta `python scripts/casos_b07_b08.py restaurar` para dejarla vacía de nuevo.
- **Empresa C:** sin cuentas (B03).
- **B07 y B08** (no hay operación para desactivar cuentas): `python scripts/casos_b07_b08.py b07` desactiva el egreso de 1000.00 de Banco; `... b08` desactiva la cuenta Banco; `... restaurar` lo deja como al inicio.
- **B14:** con Ana, `AplicarConfiguracion` con `variables/a7_b14_quitar_transactions_read.json` y, al terminar, con `a7_b14_restaurar_permisos.json`.

Consultas y variables: `operaciones.graphql` (sección Actividad 7). Resultados de referencia (26 al 30 de octubre de 2026):

| Cuenta | Saldo inicial | Ingresos | Egresos | Profit | Saldo final | En rojo |
|---|---|---|---|---|---|---|
| Banco | 1000.00 | 3000.00 | 2200.00 | 800.00 | 1800.00 | No |
| Caja | 0.00 | 500.00 | 700.00 | −200.00 | −200.00 | Sí |
| Ahorro | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | No |
| **General** | 1000.00 | 3500.00 | 2900.00 | 600.00 | 1600.00 | No (`accountsInRed: 1`) |

## Datos de demo (Actividad 6)
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
python -m pytest tests/test_balances.py -v   # balances (Actividad 7): B01-B06, B10-B13, B15 y validación de montos
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
`Evidencias act7.md` (entrega: `evidencias.md`) · `act7_evidencias/` · `investigacion.md` · `operaciones.graphql` · `variables/` · `configuracion_inicial.json` · `configuracion_final.json` · `comprobaciones.sql` · `evidencias.md` · `act5_evidencias/`
