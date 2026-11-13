# Evidencias — Unidad III, Actividad 1 (Dashboard financiero)

Datos: `python scripts/preparar_demo_actividad7.py`. Usuario: `ana@actividad7.com`.
Período: 2026-10-26 a 2026-10-30. Las capturas van en `dashboard/evidencias/` con los nombres indicados.

## Boceto del diseño
![Boceto de la vista principal](boceto.svg)

## D01 — Login
Pantalla de inicio de sesión antes de entrar (usa la mutación `login`).

![D01 Login](evidencias/D01_login.png)

## D02 — Indicadores generales
Dashboard con el período 26–30 de octubre de 2026: saldo inicial 1,000.00, ingresos 3,500.00,
egresos 2,900.00, profit 600.00, saldo final 1,600.00, general en rojo: No, cuentas en rojo: 1 (Caja).

![D02 Indicadores generales](evidencias/D02_indicadores_generales.png)

## D03 — Detalle por cuenta
Tabla con Banco, Caja (saldo final −200.00, en rojo) y Ahorro, del mismo resultado `generalBalance.accounts`.

![D03 Detalle por cuenta](evidencias/D03_detalle_por_cuenta.png)

## D04 — Caso de error: token inválido
Con la sesión abierta, en la consola del navegador (F12) ejecutar
`sessionStorage.setItem("sgi.token", "token.invalido.x")` y pulsar **Actualizar**. El dashboard vuelve
al login con el mensaje "Tu sesión expiró o el token no es válido. Inicia sesión de nuevo."

![D04 Token inválido](evidencias/D04_token_invalido.png)

## D05 — Caso de error: usuario sin permiso
En GraphiQL, con el token de Ana, ejecutar `AplicarConfiguracion` con
`variables/a7_b14_quitar_transactions_read.json`. Eso le quita `transactions.read` al rol CONSULTA.
Entrar al dashboard con `pedro@actividad7.com` (CONSULTA): aparece "Acceso denegado…" y ningún número. Al terminar, restaurar con
`variables/a7_b14_restaurar_permisos.json`.

![D05 Sin permiso](evidencias/D05_sin_permiso.png)

## D06 — Fechas inválidas
"Desde" posterior a "Hasta": el dashboard no llama al API y muestra el motivo.

![D06 Fechas inválidas](evidencias/D06_fechas_invalidas.png)

## D07 — Cambio de período
Mismo usuario con 2026-11-01 a 2026-11-13: el encabezado cambia de período, saldo inicial 1,600.00 y
el aviso de que no hay movimientos.

![D07 Cambio de período](evidencias/D07_cambio_de_periodo.png)
