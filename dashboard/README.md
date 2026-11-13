# Dashboard financiero — Unidad III, Actividad 1

Cliente web del Sistema General de Ingresos: inicia sesión, pide un período y muestra los
indicadores generales de la empresa leyendo `generalBalance` del API GraphQL.

**Integrantes:** Jesús Omar Uc Domínguez · Ángela Yaritzi Rojas Brito

## Arquitectura elegida
Página web sencilla: **HTML + CSS + JavaScript sin framework ni dependencias** (`index.html`,
`styles.css`, `app.js`) que hace `fetch` a `/graphql`.

- El backend es la única fuente de cálculo. El cliente no suma ni resta: solo da formato a los
  importes, que llegan como texto (`"1800.00"`) y se tratan como texto, sin `float`.
- Todo va por GraphQL (`login`, `generalBalance`, `company`); no hay API REST paralelo.
- El token se guarda solo en `sessionStorage` del navegador y se borra al cerrar sesión. No hay
  tokens, contraseñas ni el secreto JWT en el código.
- La empresa sale del token: el cliente no envía `companyId` ni `actorCompanyUserId`.

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
| Nombre de la empresa | `company(id: companyId).name` |
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
`index.html` · `styles.css` · `app.js` · `boceto.svg` (wireframe) · `evidencias.md` ·
`evidencias/` (capturas) · `guion_demo.md`
