# Dashboard del Sistema General de Ingresos — Unidad III

Cliente web del Sistema General de Ingresos. Una sola aplicación, con el mismo login y el mismo API
GraphQL, y dos dashboards en el menú de la izquierda:

- **Financiero** (actividad 1): período, indicadores generales y saldo por cuenta (`generalBalance`).
- **Administrativo** (actividad 2): Usuarios, Cuentas y Conceptos.
- **Roles y permisos** (actividad 3): la matriz rol × permiso, dentro del dashboard administrativo.

**Integrantes:** Jesús Omar Uc Domínguez · Ángela Yaritzi Rojas Brito

## Actividad 3: Roles y permisos
1. Desde `Actividad_5_Jesus_Uc/`: `docker compose up -d`, `python scripts/preparar_demo_u3a3.py` y
   `uvicorn app.main:app`. El script deja la matriz como la sección 2.2 de la guía y es repetible.
2. Abrir http://127.0.0.1:8000/dashboard/ y entrar. En el menú, bajo **Administración**, elegir
   **Roles y permisos** (`#/admin/roles`). El ítem solo se dibuja si `myAccess` trae `roles.read`.

| Para qué | Usuario (contraseña `Secreto123!`) | Rol |
|---|---|---|
| **Editar la matriz** y asignar puestos en Usuarios | `ana@actividad7.com` | ADMINISTRADOR (`roles.write`) |
| Ver la matriz deshabilitada (solo lectura) | `luis@actividad7.com` | CONTADOR (`roles.read`, sin `roles.write`) |
| **Comprobar el efecto** de la columna Capturista (Nueva cuenta en Cuentas) | `maria@actividad7.com` y `jose@actividad7.com` | CAPTURISTA |
| Comprobar el cambio de puesto (Consulta → Capturista: Registrar movimiento) | `pedro@actividad7.com` | CONSULTA al inicio |

Cómo funciona la pantalla:
- **De dónde sale:** columnas = `roles(activeOnly: true)`, filas = `permissions(activeOnly: true)`,
  celdas = `rolePermissions(roleId)` por columna. «Sí» es una relación activa; «no» es que no hay
  concesión (no hay marca de prohibido). Un permiso desactivado en el catálogo no se muestra.
- **Orden:** columnas Administrador, Contador, Capturista, Consulta (nombre y código de MySQL);
  filas en cinco grupos (Usuarios, Cuentas, Conceptos, Movimientos, Roles), lectura antes que
  escritura. El nombre de la fila es el `name` del permiso y el código va debajo.
- **Editar:** solo con `roles.write`. Al marcar una casilla se abre la **vista previa**
  (`previewRolePermissions`, solo lee) con lo que se activa, lo que se desactiva, cuántos quedan sin
  cambio y el total final. **Guardar columna** manda la lista completa a `setRolePermissions` y
  luego vuelve a leer la columna. **Revisar y guardar** abre la vista previa de una columna sin
  cambios: guardarla responde `changed = false` y la pantalla lo dice.
- **Administrador** se ve y no se edita; nunca se envía a `setRolePermissions`.
- Se edita una columna a la vez; las otras quedan bloqueadas hasta guardar o descartar.
- **Usuarios, columna Rol:** con `roles.write` aparece un selector con los roles activos; Guardar
  llama `assignRole`, la celda muestra lo que devolvió la mutación y la tabla se vuelve a leer.
  Un solo rol activo por membresía; `isAdmin` no cambia. El administrador principal no lleva selector.
  Si el API rechaza, el error se lee y el selector vuelve al puesto anterior.
- **Menú por permisos:** cada ítem se dibuja solo con su permiso de lectura (Capturista no ve
  Usuarios ni Roles y permisos). Si alguien escribe la dirección a mano, el API la rechaza y la
  pantalla muestra el error.
- **El token no trae permisos:** al cambiar de pantalla (o pulsar otra vez el ítem del menú) el
  dashboard vuelve a pedir `myAccess`, así que un cambio de columna o de puesto se nota sin cerrar sesión.
- **Registrar movimiento** (Resumen financiero): botón visible solo con `transactions.write`, para
  ver el efecto de esa celda. Usa `createTransaction` con `idempotencyKey`.

Backend: no hubo que cambiar las operaciones (ya leían el token desde el Parcial II). Solo se
alinearon los nombres de los permisos con la guía (`app/seed.py` y el script de la demo) y se
agregaron `tests/test_unidad3_actividad3.py` y `comprobaciones_u3a3.sql`.

## Actividad 2: cómo se entra a la administración
1. Levantar todo (ver "Cómo levantar todo" más abajo) y correr `python scripts/preparar_demo_u3a2.py`.
2. Abrir http://127.0.0.1:8000/dashboard/ e iniciar sesión con **`ana@actividad7.com`** (rol
   **ADMINISTRADOR**: es el rol que usamos para probar la escritura; tiene `company.users.write`,
   `accounts.write` y `concepts.write`).
3. En el menú, bajo **Administración**, elegir **Usuarios**, **Cuentas** o **Conceptos**. Cada pantalla
   tiene su dirección: `#/admin/usuarios`, `#/admin/cuentas`, `#/admin/conceptos`. **Resumen
   financiero** (`#/financiero`) vuelve al dashboard de la actividad 1.
4. Para ver la pantalla de solo lectura, entrar con **`pedro@actividad7.com`** (rol **CONSULTA**): ve
   las tablas, pero no los botones Nuevo usuario, Nueva cuenta, Nuevo concepto, Desactivar, Asignar ni Quitar.

El encabezado es el mismo en las dos vistas: nombre de la empresa de la sesión, usuario, rol y
**Cerrar sesión** (borra el token y vuelve al login). Si el token falta o el API lo rechaza en
cualquier pantalla, se vuelve al login; no se queda una tabla a medias.

### Qué muestra cada pantalla y de dónde sale
| Pantalla | Pregunta | Lectura | Altas y bajas | Permiso para escribir |
|---|---|---|---|---|
| Usuarios | ¿Quién pertenece a la empresa? | `companyUsers` | `createCompanyUser`, `deactivateCompanyUser` | `company.users.write` |
| Cuentas | ¿Dónde está el dinero? | `accounts` | `createAccount` | `accounts.write` |
| Conceptos | ¿Por qué se mueve el dinero y en qué cuenta se permite? | `concepts`, `accounts`, `accountConcepts` | `createConcept`, `assignConceptToAccount`, `removeConceptFromAccount` | `concepts.write` |

| En pantalla | Campo GraphQL |
|---|---|
| Usuarios: Nombre, Correo | `companyUsers.user.name`, `user.email` |
| Usuarios: Rol | `companyUsers.role.name` (rol activo guardado en `company_user_roles`; "Sin rol asignado" si es null) |
| Usuarios: Administrador, Estado | `isAdmin`, `isActive` |
| Usuarios: conteos de arriba | Calculados con la misma lista (activos, administrador principal, inactivos); no son importes |
| Cuentas: Nombre, Tipo, Banco, Estado | `name`, `accountType` (con su etiqueta: CASH → Efectivo, etc.), `bankName`, `isActive` |
| Cuentas: Referencia | `clabe` enmascarada (`****` + últimos 4) o `cardLastDigits` |
| Conceptos: Concepto, Tipo, Estado | `name`, `conceptType` (INCOME → Ingreso, EXPENSE → Egreso), `isActive` |
| Conceptos de la cuenta | `accountConcepts(accountId)` con `isActive = true` |
| Qué botones se dibujan | `myAccess.permissions` |

Reglas que se cumplen:
- Después de cada alta, baja o asignación la tabla **se vuelve a consultar**; no se agrega la fila a mano.
- Los errores del API se leen en la pantalla: correo duplicado, concepto ya asignado, nombre repetido, etc.
- Las bajas son lógicas: Desactivar y Quitar ponen `isActive` en false; la fila sigue en MySQL.
- La contraseña solo existe en el formulario de alta; no aparece en ninguna tabla ni en ninguna consulta.
- Estado vacío: si no hay usuarios, cuentas o conceptos (o ninguno coincide con el filtro) se dice con texto.
- Activo e inactivo se distinguen con una etiqueta de color y hay filtro para ver solo activos.
- Las búsquedas y filtros trabajan sobre la lista ya cargada; no hay endpoint nuevo para eso.
- El alta de usuario no pide `isAdmin`: se crea con rol Consulta. El administrador principal ya existe
  (`createCompanyAdmin`, Parcial I) y no se puede desactivar.

El diseño sigue las figuras 9 a 12 de la guía (menú a la izquierda, título, búsqueda o filtros,
acción principal y tabla; el formulario aparece a la derecha al pulsar la acción), por eso no hay un
boceto nuevo.

## Actividad 1: dashboard financiero

## Arquitectura elegida
Página web sencilla: **HTML + CSS + JavaScript sin framework ni dependencias** (`index.html`,
`styles.css`, `app.js`) que hace `fetch` a `/graphql`.

- El backend es la única fuente de cálculo. El cliente no suma ni resta: solo da formato a los
  importes, que llegan como texto (`"1800.00"`) y se tratan como texto, sin `float`.
- Todo va por GraphQL; no hay API REST paralelo.
- El token se guarda solo en `sessionStorage` del navegador y se borra al cerrar sesión. No hay
  tokens, contraseñas ni el secreto JWT en el código.
- La empresa sale del token: el cliente nunca envía `actorCompanyUserId`, y el `companyId` que
  usan las consultas de administración es el que devuelve `myAccess` (el API lo lee del token).

## Cómo levantar todo
Desde `Actividad_5_Jesus_Uc/` (backend). La primera vez: `pip install -r requirements.txt` y crear
`.env` con `JWT_SECRET` (ver el README del backend).

```
docker compose up -d                          # MySQL en el puerto 3307
python scripts/preparar_demo_actividad7.py    # datos de demostración (repetible)
uvicorn app.main:app                          # API en el puerto 8000
```

| Qué | Dónde |
|---|---|
| Dashboard | http://127.0.0.1:8000/dashboard/ |
| GraphiQL (herramienta de prueba) | http://127.0.0.1:8000/graphql |
| MySQL | 127.0.0.1:3307 (`actividad4_db`) |

**No hay un segundo proceso:** el propio API sirve la carpeta `dashboard/` en `/dashboard/`
(mismo origen, así que no interviene CORS). Si prefieren abrir el cliente desde otro puerto
(Live Server en 5500 o Vite en 5173), el backend ya permite esos orígenes por CORS y el cliente
apunta solo a `http://127.0.0.1:8000/graphql`; otros orígenes se agregan con `CORS_ORIGINS` en `.env`.

## Usuario de prueba y período de demostración
| Persona | Correo | Rol | Para qué |
|---|---|---|---|
| Ana | ana@actividad7.com | ADMINISTRADOR | Demo principal (Empresa A: Banco, Caja, Ahorro) |
| Pedro | pedro@actividad7.com | CONSULTA | Caso sin permiso (ver `evidencias.md`) |
| Admin C | adminc@actividad7.com | ADMINISTRADOR | Estado vacío (empresa sin cuentas) |

Contraseña de los usuarios de demostración: la que imprime `preparar_demo_actividad7.py`
(también está en el README del backend).

**Período de demostración:** del **2026-10-26** al **2026-10-30**. Al entrar, el dashboard propone
del día 1 del mes en curso a hoy; cambien las fechas a ese período.

| Indicador | Valor esperado |
|---|---|
| Saldo inicial | 1,000.00 |
| Ingresos | 3,500.00 |
| Egresos | 2,900.00 |
| Profit | 600.00 |
| Saldo final | 1,600.00 |
| General en rojo | No |
| Cuentas en rojo | 1 (Caja) |

## De dónde sale cada dato en pantalla
| En pantalla | Campo GraphQL (`generalBalance`) |
|---|---|
| Período del encabezado | `fromDate`, `toDate` (de la respuesta, no de los campos de fecha) |
| Moneda | `currency` |
| Nombre de la empresa | `myAccess.companyName` |
| Saldo inicial | `openingBalance` |
| Ingresos | `totalIncome` |
| Egresos | `totalExpense` |
| Profit | `profit` |
| Saldo final | `closingBalance` |
| Saldo general en rojo | `isInRed` |
| Cuentas en rojo | `accountsInRed` (nombres: `accounts` con `isInRed`) |
| Detalle por cuenta | `accounts { accountName isActive openingBalance totalIncome totalExpense profit closingBalance isInRed }` |

## Comportamiento ante errores
- **Token faltante, vencido o inválido:** se borra la sesión y se vuelve al login con un mensaje.
- **Sin permiso de lectura** (`accounts.read` / `transactions.read`): mensaje de acceso denegado y
  ningún número en pantalla.
- **Fechas inválidas** (falta una o "Desde" es posterior a "Hasta"): no se llama al API, se
  muestra el motivo y se quitan los números del período anterior.
- **Estados vacíos:** empresa sin cuentas y período sin movimientos se explican con texto.
- **Números rojos:** un saldo final negativo se marca en rojo con la etiqueta "En rojo"; un profit
  negativo solo cambia a ámbar, para no confundirlo con un saldo en rojo.

## Archivos
`index.html` · `styles.css` · `app.js` · `boceto.svg` (wireframe de la actividad 1) ·
`evidencias.md` (actividad 1) · `evidencias_actividad2.md` (actividad 2) ·
`evidencias_actividad3.md` (actividad 3) · `evidencias/` (capturas) ·
`guion_demo.md`
