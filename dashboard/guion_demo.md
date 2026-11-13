# Guion de la demostración — final del Parcial III

**Antes de empezar:** Docker Desktop abierto, `docker compose up -d`,
`python scripts/preparar_demo_actividad7.py` y `uvicorn app.main:app` (desde `Actividad_5_Jesus_Uc/`).
Navegador en http://127.0.0.1:8000/dashboard/.

1. **Login con un usuario real de la base.** Entrar con `ana@actividad7.com`. Mencionar que se usa
   la mutación `login` y que el token queda solo en `sessionStorage`.
2. **Apertura del dashboard.** Señalar los cinco bloques del boceto: encabezado (empresa, MXN y
   período), controles, indicadores generales, estado de riesgo y detalle por cuenta.
3. **Consulta de un período.** Poner Desde `2026-10-26` y Hasta `2026-10-30`. Leer los indicadores:
   saldo inicial 1,000.00, ingresos 3,500.00, egresos 2,900.00, profit 600.00, saldo final 1,600.00.
   Explicar que cada tarjeta es un campo de `generalBalance` y que el cliente no recalcula nada.
4. **Cuenta en rojo con total positivo.** Mostrar "Saldo general en rojo: No" junto a
   "Cuentas en rojo: 1 (Caja)" y la fila de Caja con saldo final −200.00 marcado en rojo.
5. **Cambio de fechas.** Cambiar a `2026-11-01` – `2026-11-13`: el período del encabezado y los
   números se actualizan (saldo inicial 1,600.00, sin movimientos). Probar también "Desde" posterior
   a "Hasta" para mostrar el mensaje de fechas inválidas.
6. **Caso de error (si hay tiempo).** Entrar con un usuario sin permiso de lectura o con un token
   inválido y mostrar el mensaje en lugar de números.
7. **Cerrar sesión.** Vuelve al login y el token se borra.

Comprobación cruzada, por si la piden: la misma consulta `generalBalance` en GraphiQL con las mismas
fechas devuelve las mismas cifras que el dashboard.
