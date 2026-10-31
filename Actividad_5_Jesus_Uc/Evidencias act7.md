# Actividad 7 — Balances por cuenta y balance general

Sistema General de Ingresos (Python, Strawberry, GraphQL, SQLAlchemy, MySQL).
Integrantes: Jesús Omar Uc Domínguez · Ángela Yaritzi Rojas Brito.

Todos los importes son MXN y todas las fechas y horas son UTC. Periodo de referencia: **26 al 30 de octubre de 2026**.
Los datos se preparan con `python scripts/preparar_demo_actividad7.py` (restaura siempre el mismo estado) y las variables de cada consulta están en `variables/a7_*.json`.

## Conjunto inicial (Parte 1)

Movimientos activos, todos a las 12:00:00Z:

| Cuenta | Fecha de operación | Tipo | Importe | Descripción |
|---|---|---|---|---|
| Banco | 25 oct 2026 | INCOME | 1000.00 | Ingreso de apertura anterior al período |
| Banco | 26 oct 2026 | INCOME | 3000.00 | Cobro de servicios |
| Banco | 27 oct 2026 | EXPENSE | 1200.00 | Pago de renta |
| Banco | 28 oct 2026 | EXPENSE | 1000.00 | Compra de materiales |
| Caja | 26 oct 2026 | INCOME | 500.00 | Venta de contado |
| Caja | 29 oct 2026 | EXPENSE | 700.00 | Pago de insumos |
| Ahorro | — | — | — | Cuenta que debe aparecer con ceros |

Tabla calculada a mano antes de programar:

| Cuenta | Saldo inicial | Ingresos | Egresos | Profit | Saldo final | En rojo |
|---|---|---|---|---|---|---|
| Banco | 1000.00 | 3000.00 | 2200.00 | 800.00 | 1800.00 | No |
| Caja | 0.00 | 500.00 | 700.00 | −200.00 | −200.00 | Sí |
| Ahorro | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | No |
| **General** | 1000.00 | 3500.00 | 2900.00 | 600.00 | 1600.00 | No |

![Conjunto inicial en MySQL](act7_evidencias/inicial_sql.png)

## Los casos

### B01 — Banco, Caja, Ahorro y general (26 al 30)
Consultas `BalanceDeUnaCuenta` (con `a7_balance_banco/caja/ahorro.json`) y `BalanceDeLaEmpresa` (`a7_balance_general.json`), con el token de Ana.

![B01 Banco](act7_evidencias/B01_banco.png)
![B01 Caja](act7_evidencias/B01_caja.png)
![B01 Ahorro](act7_evidencias/B01_ahorro.png)
![B01 General](act7_evidencias/B01_general.png)
![B01 Conteo de movimientos antes y después](act7_evidencias/B01_conteo.png)

**Resultado obtenido:** Banco `1000.00 / 3000.00 / 2200.00 / 800.00 / 1800.00` sin números rojos; Caja `0.00 / 500.00 / 700.00 / −200.00 / −200.00` con `isInRed: true`; Ahorro en `0.00`; general `1000.00 / 3500.00 / 2900.00 / 600.00 / 1600.00`, `isInRed: false`, `accountsInRed: 1`. El conteo de `transactions` es el mismo antes y después.
**Regla comprobada:** el saldo inicial sale de los movimientos anteriores al periodo, y las consultas solo leen: no crean ni modifican filas.

### B02 — Banco solo el 28
![B02](act7_evidencias/B02.png)

**Resultado obtenido:** saldo inicial `2800.00`, ingresos `0.00`, egresos `1000.00`, profit `−1000.00`, saldo final `1800.00`, `isInRed: false`.
**Regla comprobada:** un profit negativo del día no implica un saldo final negativo, porque el dinero previo también cuenta.

### B03 — Empresa sin cuentas
Con el token de Admin C (`adminc@actividad7.com`).

![B03](act7_evidencias/B03.png)

**Resultado obtenido:** `accounts: []`, todos los importes en `"0.00"`, `accountsInRed: 0`, `isInRed: false`.
**Regla comprobada:** una empresa sin cuentas devuelve ceros y una lista vacía, no `null`.

### B04 — Bordes del periodo
Con el token de Admin B, en `Cuenta Prueba B`, se capturan cuatro movimientos con `transactionDate` `2026-10-25T23:59:59Z`, `2026-10-26T00:00:00Z`, `2026-10-30T23:59:59Z` y `2026-10-31T00:00:00Z`.

![B04 Movimientos guardados](act7_evidencias/B04_capturas.png)
![B04 Balance](act7_evidencias/B04_balance.png)

**Resultado obtenido:** saldo inicial `1.00`, ingresos `10.00`, egresos `4.00`, profit `6.00`, saldo final `7.00`.
**Regla comprobada:** el inicio es inclusivo y el fin es la medianoche del día siguiente a `toDate`, excluida; el movimiento de las 23:59:59 del 25 solo afecta el saldo inicial y el de la medianoche del 31 queda fuera.

### B05 — Movimiento del 27 capturado después
![B05 Captura](act7_evidencias/B05.png)
![B05 Balance del 27](act7_evidencias/B05_balance.png)

**Resultado obtenido:** el egreso de `75.00` se guarda con `transactionDate` `2026-10-27T12:00:00Z` y `capturedAt` `2026-10-31T05:11:28Z` (el instante real de la captura). El balance del 27 muestra egresos `75.00`, profit `−75.00` y saldo final `−75.00`.
**Regla comprobada:** el balance usa `transaction_date`, nunca `captured_at`.

### B06 — Centavos exactos
Con ingresos de `0.10` y `0.20` y un egreso de `0.30` el 27 de octubre.

![B06](act7_evidencias/B06.png)

**Resultado obtenido:** ingresos `"0.30"`, egresos `"0.30"`, profit `"0.00"`, saldo final `"0.00"`, `isInRed: false`.
**Regla comprobada:** con `Decimal` la suma es exacta (con `float`, 0.1 + 0.2 − 0.3 no da 0).

### B07 — Movimiento inactivo
Se desactiva el egreso de `1000.00` de Banco con `python scripts/casos_b07_b08.py b07`.

![B07 Balance](act7_evidencias/B07.png)
![B07 Movimientos en MySQL](act7_evidencias/B07_sql.png)

**Resultado obtenido:** Banco ingresos `3000.00`, egresos `1200.00`, profit `1800.00`, saldo final `2800.00`. En MySQL el movimiento queda con `is_active = 0` y los otros tres siguen intactos.
**Regla comprobada:** un movimiento inactivo deja de participar en el balance, pero no se borra.

### B08 — Cuenta desactivada
Se desactiva la cuenta Banco con `python scripts/casos_b07_b08.py b08`.

![B08](act7_evidencias/B08.png)

**Resultado obtenido:** Banco sigue en el balance con `isActive: false` y saldo final `1800.00`; el general no cambia (`1600.00`).
**Regla comprobada:** desactivar una cuenta no borra su historial ni su aportación al total.

### B09 — Otro concepto permitido, sin movimientos nuevos
Con la mutación `AsignarConcepto` (`a7_b09_asignar_concepto.json`) se agrega otro concepto de ingreso a Banco.

![B09 Asignación del concepto](act7_evidencias/B09.png)
![B09 General sin cambios](act7_evidencias/B09_general.png)

**Resultado obtenido:** la asignación se guarda y el balance general conserva los mismos totales (`1000.00 / 3500.00 / 2900.00 / 600.00 / 1600.00`).
**Regla comprobada:** el balance depende de `transaction_type` de cada movimiento, no de las relaciones cuenta-concepto; agregar una no duplica ni cambia importes.

### B10 — Fechas inválidas
![B10 fromDate posterior a toDate](act7_evidencias/B10.png)
![B10 fecha inexistente](act7_evidencias/B10_inexistente.png)

**Resultado obtenido:** con `fromDate` posterior a `toDate` y con una fecha inexistente, GraphQL responde `errors` y `data: null`; no se calcula balance.
**Regla comprobada:** las fechas se validan antes de consultar; un solo día (`from = to`) sí es válido (B02).

### B11 — Sin token, alterado y vencido
![B11 Sin token](act7_evidencias/B11_sin_token.png)
![B11 Token alterado](act7_evidencias/B11_alterado.png)
![B11 Token vencido](act7_evidencias/B11_vencido.png)

**Resultado obtenido:** en los tres casos la consulta responde `errors` y `data: null` (sin token: `Falta el token`; alterado y vencido: `El token no es válido`). El mismo resultado se obtiene con `generalBalance`.
**Regla comprobada:** ambas consultas validan el token antes de devolver cualquier dato.

### B12 — Cuenta de otra empresa
Con el token de Ana (empresa A) se consulta la cuenta de la empresa B y, para comparar, una cuenta inexistente.

![B12 Cuenta de otra empresa](act7_evidencias/B12.png)
![B12 Cuenta inexistente](act7_evidencias/B12_inexistente.png)

**Resultado obtenido:** en ambos casos el error es el mismo, `Cuenta no disponible.`, sin nombres ni importes de la otra empresa. El balance general de Ana solo contiene Banco, Caja y Ahorro (también lo comprueba `test_b12_cuenta_de_otra_empresa_no_revela_datos`).
**Regla comprobada:** la empresa sale del token; una cuenta ajena y una inexistente responden igual y no revelan datos.

### B13 — Rol CONSULTA
Con el token de Pedro.

![B13 Lectura de los balances](act7_evidencias/B13_lectura.png)
![B13 Captura rechazada](act7_evidencias/B13_captura.png)
![B13 Conteo de movimientos](act7_evidencias/B13_conteo.png)

**Resultado obtenido:** Pedro lee el balance de Banco y el general; `createTransaction` responde `El rol no tiene el permiso transactions.write` y el conteo de `transactions` no cambia.
**Regla comprobada:** CONSULTA puede leer balances (`accounts.read` y `transactions.read`), pero no tiene `transactions.write`.

### B14 — Sin `transactions.read`
Ana quita `transactions.read` al rol CONSULTA y Pedro repite las consultas con el **mismo token**; después se restaura el permiso.

![B14 Ana quita el permiso](act7_evidencias/B14_quitar.png)
![B14 Pedro rechazado](act7_evidencias/B14_rechazo.png)
![B14 Permiso restaurado](act7_evidencias/B14_restaurar.png)

**Resultado obtenido:** al quitar el permiso, el mismo token de Pedro deja de acceder a `accountBalance` y `generalBalance` (`El rol no tiene el permiso transactions.read`), aunque conserva `accounts.read`. Al restaurarlo, el acceso vuelve.
**Regla comprobada:** los permisos se leen de MySQL en cada petición y ambas consultas exigen `accounts.read` **y** `transactions.read`.

### B15 — Egreso en cuenta vacía
Con el token de Admin B, un egreso de `50.00` en la cuenta vacía.

![B15 Balance de la cuenta](act7_evidencias/B15.png)
![B15 Balance general de la empresa](act7_evidencias/B15_general.png)

**Resultado obtenido:** el egreso se guarda con monto `50.00` (positivo); la cuenta queda con egresos `50.00`, profit `−50.00` y saldo final `−50.00` (`isInRed: true`). El general de esa empresa queda en `−50.00`, `isInRed: true`, `accountsInRed: 1`.
**Regla comprobada:** el monto siempre es positivo y el tipo `EXPENSE` es el que resta; el backend permite el saldo negativo y lo informa.

## Pruebas automatizadas

`python -m pytest -v` — 57 pruebas pasando. Las de `tests/test_balances.py` cubren B01, B02, B03, B04 (incluida la normalización a UTC de fechas con zona), B05, B06, B10, B11, B12, B13, B15 y la validación de montos. Los resultados esperados están escritos a mano a partir de los datos de entrada, sin usar el servicio de balances.

![Resultado de pytest](act7_evidencias/pytest.png)

## Explicación breve: saldo inicial, profit, saldo final y números rojos

Con los datos del 26 al 30 de octubre, **Banco** empieza el periodo con 1000.00 (el ingreso de apertura del día 25), recibe 3000.00 y paga 2200.00. Su profit es 3000.00 − 2200.00 = **800.00** y su saldo final es 1000.00 + 800.00 = **1800.00**: el profit mide solo lo que pasó dentro del periodo, y el saldo final suma además el dinero que ya tenía.

**Caja** empieza en 0.00, recibe 500.00 y paga 700.00: su profit es **−200.00** y, como no tenía dinero previo, su saldo final también es **−200.00**, así que está en números rojos (`isInRed = closingBalance < 0`). Un profit negativo no basta para estar en rojo (Banco el día 28 tiene profit −1000.00 y saldo final 1800.00), y un total positivo no esconde una cuenta negativa: el general suma 1600.00 (`isInRed: false`), pero `accountsInRed: 1` avisa que Caja sí lo está.
