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
- **Obtenido:**
- **Regla:** `roles.read` permite consultar roles y sus permisos activos.

## E02 - Catálogo de permisos y enum inválido

- **Precondición:** permisos del seed activos.
- **Operación y variables:** `ExplorarCatalogo`, `CatalogoCompleto` y
  `CatalogoPorRecurso` con `variables/e02_catalogo.json`;
  `CatalogoPorRecurso` con `variables/e02_enum_invalido.json` (recurso `PAYMENTS`).
- **Esperado:** catálogo ordenado por código y filtrado por prefijo del recurso;
  con `PAYMENTS` GraphQL rechaza el valor del enum (error de validación).
- **Obtenido:**
- **Regla:** el catálogo solo muestra permisos activos y `resource` es el enum
  `PermissionResource`.

## E03 - Vista previa de S1

- **Precondición:** CAPTURISTA en S0.
- **Operación y variables:** `RevisarConfiguracion` con
  `variables/e03_e04_e05_s1.json`.
- **Esperado:** toActivate = [accounts.write]; toDeactivate = []; unchanged = 4;
  finalCount = 5; la BD no cambia.
- **Obtenido:**
- **Regla:** la vista previa no escribe ni hace commit.

## E04 - Aplicar S1

- **Precondición:** CAPTURISTA en S0.
- **Operación y variables:** `AplicarConfiguracion` con
  `variables/e03_e04_e05_s1.json`.
- **Esperado:** changed = true; activated = [accounts.write]; deactivated = [];
  finalCount = 5.
- **Obtenido:**
- **Regla:** un solo commit; requiere `roles.write`.

## E05 - Idempotencia y reactivación

- **Precondición:** CAPTURISTA en S1 (tras E04).
- **Operación y variables:** `AplicarConfiguracion` con
  `variables/e03_e04_e05_s1.json` (segunda vez); luego con
  `variables/e05_e09_s0.json` y de nuevo con S1.
- **Esperado:** la segunda aplicación de S1 da changed = false con activated y
  deactivated vacíos; tras S0 y S1, accounts.write conserva el mismo
  `relacion_id`; sin parejas duplicadas.
- **Obtenido:**
- **Regla:** se reactiva la fila existente, no se borra ni se duplica
  (`uq_role_permission`).

## E06 - Propuestas inválidas

- **Precondición:** CAPTURISTA en S0. Para rol y permiso inactivos, ejecutar
  antes la preparación de `comprobaciones.sql` y restaurar al terminar.
- **Operación y variables:** `AplicarConfiguracion` (y `RevisarConfiguracion`) con
  `e06_rol_inexistente`, `e06_administrador`, `e06_permiso_inexistente`,
  `e06_permiso_repetido`, `e06_rol_inactivo`, `e06_permiso_inactivo`.
- **Esperado:** error en cada caso y estado de BD sin cambios.
- **Obtenido:**
- **Regla:** se valida todo antes de modificar; ADMINISTRADOR es rol protegido;
  rol y permisos deben existir y estar activos; sin ids repetidos.

## E07 - Rollback si falla antes del commit

- **Precondición:** CAPTURISTA en S0.
- **Operación y variables:** prueba automatizada
  `test_e07_rollback_si_falla_antes_del_commit` en
  `tests/test_set_role_permissions.py` (falla simulada de `commit` tras el flush).
- **Esperado:** hay error y, con una sesión nueva, CAPTURISTA queda idéntico.
- **Obtenido:**
- **Regla:** la operación es atómica; ante cualquier excepción se hace rollback.

## E08 - Lista vacía

- **Precondición:** CAPTURISTA en S0.
- **Operación y variables:** `AplicarConfiguracion` con `variables/e08_vacia.json`;
  luego reiniciar la aplicación (seed de arranque).
- **Esperado:** 0 relaciones activas; tras el arranque siguen en 0 y las filas se
  conservan.
- **Obtenido:**
- **Regla:** el seed solo siembra roles sin ninguna fila en `role_permissions`.

## E09 - Restaurar S0

- **Precondición:** CAPTURISTA en cualquier estado de prueba (p. ej. vacío).
- **Operación y variables:** `AplicarConfiguracion` con
  `variables/e05_e09_s0.json`.
- **Esperado:** CAPTURISTA vuelve a S0 (4 activas); las filas inactivas se
  conservan.
- **Obtenido:**
- **Regla:** la configuración es reversible sin borrar relaciones.

## E10 - Verificación final en BD

- **Precondición:** casos E01 a E09 ejecutados.
- **Operación y variables:** consultas de `comprobaciones.sql` (relaciones,
  duplicados, concesiones activas de CAPTURISTA, conteos, `SHOW CREATE TABLE`).
- **Esperado:** consulta de duplicados con cero filas; CAPTURISTA en S0; roles y
  permisos restaurados a activos.
- **Obtenido:**
- **Regla:** unicidad (`role_id`, `permission_id`) y coherencia con
  `configuracion_inicial.json`.
