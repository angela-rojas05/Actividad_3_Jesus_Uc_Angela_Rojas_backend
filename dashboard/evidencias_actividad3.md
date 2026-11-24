# Evidencias — Unidad III, Actividad 3 (Matriz de roles y permisos)

Datos: `python scripts/preparar_demo_u3a3.py` (desde `Actividad_5_Jesus_Uc/`). Empresa: Empresa Balances A7.
La matriz se edita con `ana@actividad7.com` (ADMINISTRADOR) y el efecto se comprueba con
`maria@actividad7.com` y `jose@actividad7.com` (CAPTURISTA) y `pedro@actividad7.com` (CONSULTA).
Las capturas están en `dashboard/evidencias/`.

### A3_E01 — La matriz inicial
Sesión de Ana: los diez permisos en cinco grupos y las cuatro columnas coinciden con la tabla de la sección 2.2; Administrador es de solo lectura.

![A3_E01 Matriz inicial](evidencias/A3_E01_matriz_inicial.png)

### A3_E02 — La columna Capturista en GraphiQL
`rolePermissions` del rol CAPTURISTA devuelve las mismas cuatro relaciones activas que la columna de la pantalla.

![A3_E02 rolePermissions de Capturista](evidencias/A3_E02_graphiql_capturista.png)

### A3_E03 — Vista previa: activar accounts.write
Al marcar Crear cuentas en Capturista, `previewRolePermissions` anuncia: se activa `accounts.write`, no se desactiva nada, 4 sin cambio, total final 5.

![A3_E03 Vista previa](evidencias/A3_E03_vista_previa.png)

### A3_E04 — Cuentas de la capturista antes y después del guardado
Antes, María ve la tabla de Cuentas sin el botón Nueva cuenta; después de guardar la columna, el botón aparece sin que se editara su fila en Usuarios.

![A3_E04a Cuentas antes](evidencias/A3_E04a_capturista_cuentas_antes.png)

![A3_E04b Cuentas después](evidencias/A3_E04b_capturista_cuentas_despues.png)

José, el segundo capturista, también ve Nueva cuenta: la celda es del puesto, no de la persona.

![A3_E04c Segundo capturista](evidencias/A3_E04c_segundo_capturista.png)

### A3_E05 — Cambio de puesto de Consulta a Capturista
En Usuarios, Pedro pasa de Consulta a Capturista con `assignRole`; isAdmin sigue en No.

![A3_E05a Usuarios](evidencias/A3_E05a_usuarios_cambio_de_puesto.png)

La columna Consulta de la matriz sigue igual después del cambio de puesto.

![A3_E05b Columna Consulta sin cambios](evidencias/A3_E05b_matriz_consulta_igual.png)

### A3_E06 — Segundo guardado de la misma columna
Guardar otra vez la columna Capturista sin cambios responde `changed = false` y no duplica filas.

![A3_E06 changed en false](evidencias/A3_E06_segundo_guardado_changed_false.png)

### A3_E07 — Sin roles.write no se guarda; sin roles.read no se ve
El contador ve la matriz deshabilitada y sin botones de guardar.

![A3_E07a Contador en solo lectura](evidencias/A3_E07a_contador_solo_lectura.png)

La capturista no tiene el ítem Roles y permisos en el menú.

![A3_E07b Capturista sin el ítem](evidencias/A3_E07b_capturista_sin_menu.png)

### A3_E08 — El mismo token ya puede registrar un movimiento
Pedro, con la sesión que abrió siendo Consulta, ve Registrar movimiento en su siguiente petición y registra un ingreso: el servidor volvió a leer `company_user_roles`.

![A3_E08 Pedro registra un movimiento](evidencias/A3_E08_pedro_mismo_token.png)

### A3_E09 — MySQL
La columna Capturista con `accounts.write` activa, cero parejas repetidas y un solo rol activo por persona (`comprobaciones_u3a3.sql`).

![A3_E09 Comprobaciones SQL](evidencias/A3_E09_mysql.png)
