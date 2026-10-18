# Evidencias - Actividad 5

Actor: membresía de Ana (ADMINISTRADOR). Variables generadas con
`python scripts/generar_variables_actividad5.py <id_ana>` en `variables/`.
Operaciones en `operaciones.graphql`; verificación SQL en `comprobaciones.sql`.

> Los casos E09 y E10 no tienen archivo de variables propio; su descripción es
> una interpretación y debe contrastarse con el PDF de la actividad.

---

## E01 - Listar roles y permisos de un rol

- **Precondición:** BD sembrada; CAPTURISTA en S0 (accounts.read, concepts.read,
  transactions.read, transactions.write).
- **Operación y variables:** `ListarRoles` con `variables/e01_listar.json`;
  `ListaDeUnRol` con `variables/e01_lista_capturista.json`.
- **Esperado:** cuatro roles; CAPTURISTA con 4 relaciones activas.
- **Obtenido:** `ListarRoles` devolvió los cuatro roles (ADMINISTRADOR, CONTADOR, CAPTURISTA y CONSULTA) y `ListaDeUnRol` con CAPTURISTA devolvió sus 4 relaciones activas (accounts.read, concepts.read, transactions.read y transactions.write), que coinciden con `configuracion_inicial.json`. Capturas: `E01/01 - Roles.png`, `E01/01 - SQL.png`, `E01/02 - Permisos.png` y `E01/03 - Lista del Capturista.png`.
- **Regla:** `roles.read` permite consultar roles y sus permisos activos.

## E02 - Catálogo de permisos y enum inválido

- **Precondición:** permisos del seed activos.
- **Operación y variables:** `ExplorarCatalogo`, `CatalogoCompleto` y
  `CatalogoPorRecurso` con `variables/e02_catalogo.json`;
  `CatalogoPorRecurso` con `variables/e02_enum_invalido.json` (recurso `PAYMENTS`).
- **Esperado:** catálogo ordenado por código y filtrado por prefijo del recurso;
  con `PAYMENTS` GraphQL rechaza el valor del enum (error de validación).
- **Obtenido:** el catálogo se obtuvo completo y filtrado por recurso, y con el recurso `PAYMENTS` GraphQL rechazó la variable con el error "Value 'PAYMENTS' does not exist in 'PermissionResource' enum" y `data: null`. Capturas: `E02/01 - Catalogo.png`, `E02/02 - Completo.png` y `E02/03 - Error.png`.
- **Regla:** el catálogo solo muestra permisos activos y `resource` es el enum
  `PermissionResource`.

## E03 - Vista previa de S1

- **Precondición:** CAPTURISTA en S0.
- **Operación y variables:** `RevisarConfiguracion` con
  `variables/e03_e04_e05_s1.json`.
- **Esperado:** toActivate = [accounts.write]; toDeactivate = []; unchanged = 4;
  finalCount = 5; la BD no cambia.
- **Obtenido:** la vista previa de CAPTURISTA mostró `toActivate` = [accounts.write], `toDeactivate` vacío, 4 permisos en `unchanged` y `finalCount` 5. Capturas: `E03/01 - SQL_antes.png` y `E03/02 - Preview.png`.
- **Regla:** la vista previa no escribe ni hace commit.

## E04 - Aplicar S1

- **Precondición:** CAPTURISTA en S0.
- **Operación y variables:** `AplicarConfiguracion` con
  `variables/e03_e04_e05_s1.json`.
- **Esperado:** changed = true; activated = [accounts.write]; deactivated = [];
  finalCount = 5.
- **Obtenido:** la primera aplicación de S1 dio `changed: true` con accounts.write en `activated` y `finalCount` 5; la segunda aplicación idéntica dio `changed: false` con `activated` y `deactivated` vacíos y `finalCount` 5. Capturas: `E04/01 - Primera.png` y `E04/03 - Segunda.png`; además `E04/02 -  Empty.png` muestra la consulta SQL de relaciones y la consulta de duplicados sin filas.
- **Regla:** un solo commit; requiere `roles.write`.

## E05 - Idempotencia y reactivación

- **Precondición:** CAPTURISTA en S1 (tras E04).
- **Operación y variables:** `AplicarConfiguracion` con
  `variables/e03_e04_e05_s1.json` (segunda vez); luego con
  `variables/e05_e09_s0.json` y de nuevo con S1.
- **Esperado:** la segunda aplicación de S1 da changed = false con activated y
  deactivated vacíos; tras S0 y S1, accounts.write conserva el mismo
  `relacion_id`; sin parejas duplicadas.
- **Obtenido:** la segunda aplicación de S1 no cambió nada (`changed: false`, ver `E04/03 - Segunda.png`); después de aplicar S0 y volver a S1, accounts.write se reactivó (`activated` = [accounts.write], `changed: true`, `finalCount` 5). Captura: `E05/01 - Desactivar y activar.png`.
- **Regla:** se reactiva la fila existente, no se borra ni se duplica
  (`uq_role_permission`).

## E06 - Propuestas inválidas

- **Precondición:** CAPTURISTA en S0. Para rol y permiso inactivos, ejecutar
  antes la preparación de `comprobaciones.sql` y restaurar al terminar.
- **Operación y variables:** `AplicarConfiguracion` (y `RevisarConfiguracion`) con
  `e06_rol_inexistente`, `e06_administrador`, `e06_permiso_inexistente`,
  `e06_permiso_repetido`, `e06_rol_inactivo`, `e06_permiso_inactivo`.
- **Esperado:** error en cada caso y estado de BD sin cambios.
- **Obtenido:** las seis propuestas inválidas fallaron con error y `data: null` tanto en `RevisarConfiguracion` como en `AplicarConfiguracion`; la consulta SQL de CAPTURISTA después de las pruebas quedó idéntica a la de antes (5 relaciones activas). Capturas: `E06/00 - SQL antes.png`, `E06/01 - Rol inexistente.png`, `E06/02 - Administrador.png` y `E06/04 - SQL despues.png`.

  | # | Variante | Mensaje obtenido |
  |---|---|---|
  | 1 | Rol inexistente | El rol no existe. |
  | 2 | ADMINISTRADOR | No se permite configurar el rol ADMINISTRADOR con esta operación. |
  | 3 | Permiso inexistente mezclado | Permisos inexistentes: 99999. |
  | 4 | Permiso repetido | IDs de permiso repetidos: 3. |
  | 5 | Rol inactivo | El rol está inactivo. |
  | 6 | Permiso inactivo | Permisos inactivos: concepts.write. |
- **Regla:** se valida todo antes de modificar; ADMINISTRADOR es rol protegido;
  rol y permisos deben existir y estar activos; sin ids repetidos.

## E07 - Rollback si falla antes del commit

- **Precondición:** CAPTURISTA en S0.
- **Operación y variables:** prueba automatizada
  `test_e07_rollback_si_falla_antes_del_commit` en
  `tests/test_set_role_permissions.py` (falla simulada de `commit` tras el flush).
- **Esperado:** hay error y, con una sesión nueva, CAPTURISTA queda idéntico.
- **Obtenido:** la prueba `test_e07_rollback_si_falla_antes_del_commit` terminó en `PASSED` (1 passed): con la falla simulada hubo error y, con una sesión nueva, CAPTURISTA quedó idéntico. Captura: `E07/01 - Pytest.png`.
- **Regla:** la operación es atómica; ante cualquier excepción se hace rollback.

## E08 - Lista vacía

- **Precondición:** CAPTURISTA en S0.
- **Operación y variables:** `AplicarConfiguracion` con `variables/e08_vacia.json`;
  luego reiniciar la aplicación (seed de arranque).
- **Esperado:** 0 relaciones activas; tras el arranque siguen en 0 y las filas se
  conservan.
- **Obtenido:** al aplicar la lista vacía, CAPTURISTA quedó con 0 relaciones activas (`rolePermissions: []`); tras reiniciar el servidor siguió en `[]`, sus 5 filas se conservaron como inactivas y los conteos fueron 4 roles y 10 permisos. Capturas: `E08/01 - Vacia.png`, `E08/02 - Reinicio.png` y `E08/03 - Despues del reinicio.png`.
- **Regla:** el seed solo siembra roles sin ninguna fila en `role_permissions`.

## E09 - Restaurar S0

- **Precondición:** CAPTURISTA en cualquier estado de prueba (p. ej. vacío).
- **Operación y variables:** `AplicarConfiguracion` con
  `variables/e05_e09_s0.json`.
- **Esperado:** CAPTURISTA vuelve a S0 (4 activas); las filas inactivas se
  conservan.
- **Obtenido:** al aplicar S0, CAPTURISTA volvió a 4 permisos activos y las listas por rol quedaron en ADMINISTRADOR 10, CONTADOR 8, CAPTURISTA 4 y CONSULTA 4; `configuracion_final.json` salió idéntica a `configuracion_inicial.json` y la consulta de duplicados dio `Empty set`. Capturas: `E09/01 - Apply S0.png`, `E09/02 - Roles.png` y `E09/03 - SQL.png`.
- **Regla:** la configuración es reversible sin borrar relaciones.

## E10 - Verificación final en BD

- **Precondición:** casos E01 a E09 ejecutados.
- **Operación y variables:** consultas de `comprobaciones.sql` (relaciones,
  duplicados, concesiones activas de CAPTURISTA, conteos, `SHOW CREATE TABLE`).
- **Esperado:** consulta de duplicados con cero filas; CAPTURISTA en S0; roles y
  permisos restaurados a activos.
- **Obtenido:** `ListarCuentas` devolvió las cuentas de la empresa y `CrearMovimiento` con María (CAPTURISTA) registró un ingreso de 150.00 en la cuenta y el concepto indicados; la consulta `SELECT * FROM transactions ORDER BY id DESC LIMIT 1` mostró ese mismo movimiento guardado. Capturas: `E10/01 - Cuentas.png` y `E10/02 - Movimiento.png`.
- **Regla:** unicidad (`role_id`, `permission_id`) y coherencia con
  `configuracion_inicial.json`.
