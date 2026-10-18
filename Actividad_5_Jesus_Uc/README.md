# Sistema General de Ingresos — Unidad II, Actividad 5

Configuración de permisos por rol con GraphQL: catálogo filtrable, previsualización y aplicación atómica
de la lista completa de un rol.

## Integrantes y aportaciones
- Jesús Omar Uc Domínguez — implementó la configuración de permisos por rol (`app/role_config.py` y `app/schema.py`), escribió las pruebas automatizadas (`tests/test_set_role_permissions.py`) y capturó las evidencias E01 a E05.
- Ángela Yaritzi Rojas Brito — preparó su propio entorno y base de datos, capturó las evidencias E06 a E10, generó la matriz final (`configuracion_final.json`), completó `evidencias.md` y redactó `investigacion.md`.

## Dependencias
Python 3.12, Docker Desktop. `pip install -r requirements.txt`
(FastAPI, Strawberry, SQLAlchemy, PyMySQL, python-dotenv, pytest, requests).

## Iniciar API y MySQL
```
copy .env.example .env
docker compose up -d
uvicorn app.main:app
```
GraphiQL: http://127.0.0.1:8000/graphql

## Preparar datos
```
python scripts/preparar_demo_actividad4.py
python scripts/generar_variables_actividad5.py ID_DE_ANA
```
El primer comando imprime los IDs de la empresa y los usuarios. El segundo escribe `variables/*.json` con los IDs reales.

## Ejecutar operaciones
Abre `operaciones.graphql`, copia UNA operación a GraphiQL y pega el JSON correspondiente en Variables:

| Operación | Variables |
|---|---|
| ListarRoles / ListarPermisos | variables/e01_listar.json |
| ListaDeUnRol | variables/e01_lista_capturista.json |
| ExplorarCatalogo / CatalogoCompleto | variables/e02_catalogo.json |
| CatalogoPorRecurso (PAYMENTS) | variables/e02_enum_invalido.json |
| RevisarConfiguracion / AplicarConfiguracion (S1) | variables/e03_e04_e05_s1.json |
| AplicarConfiguracion (S0) | variables/e05_e09_s0.json |
| AplicarConfiguracion ([]) | variables/e08_vacia.json |
| Variantes inválidas (E06) | variables/e06_*.json |

## Pruebas (E07)
```
python -m pytest tests/test_set_role_permissions.py -v
```
E07 es `test_e07_rollback_si_falla_antes_del_commit`.

## Matriz final
```
python scripts/generar_configuracion_final.py
```

## Archivos
`investigacion.md` · `operaciones.graphql` · `variables/` · `configuracion_inicial.json` · `configuracion_final.json` · `comprobaciones.sql` · `evidencias.md` · `act5_evidencias/`
