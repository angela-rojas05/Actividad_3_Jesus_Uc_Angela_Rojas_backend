# Pasos pendientes — Unidad III, Actividad 3 (Matriz de roles y permisos)

El código ya está hecho, probado y subido a la rama `actividad3u3` (79 pruebas automáticas pasan y el
dashboard se probó en el navegador). Falta: **tomar 13 capturas, hacer el commit, hacer el push y
armar el ZIP.** Son unos 30 a 40 minutos.

> **Importante:** sigue los pasos **en este orden**. Cada paso deja los datos para la captura siguiente.
> Si algo sale mal, cierra todas las pestañas del dashboard, corre otra vez
> `python scripts/preparar_demo_u3a3.py` y vuelve a empezar desde el paso 2.

## 0. Traer la rama

Desde la carpeta del repositorio:

```
git fetch origin
git switch actividad3u3
git pull
```

## 1. Levantar el proyecto

Abre Docker Desktop y espera a que termine de iniciar. En una terminal, desde `Actividad_5_Jesus_Uc/`
(si no tienes el archivo `.env`, créalo antes como dice el README de esa carpeta, sección
"Configuración: JWT_SECRET"):

```
pip install -r requirements.txt
docker compose up -d
python scripts/preparar_demo_u3a3.py
uvicorn app.main:app
```

- `preparar_demo_u3a3.py` deja la matriz como la sección 2.2 de la guía, a Pedro en Consulta y a
  María y José en Capturista. Se puede correr las veces que haga falta.
- Deja esa terminal abierta mientras tomas las capturas.

**Usuarios (contraseña de todos: `Secreto123!`):**

| Persona | Correo | Rol al inicio |
|---|---|---|
| Ana | `ana@actividad7.com` | Administrador (edita la matriz) |
| Luis | `luis@actividad7.com` | Contador (ve la matriz sin poder guardar) |
| María | `maria@actividad7.com` | Capturista |
| José | `jose@actividad7.com` | Capturista |
| Pedro | `pedro@actividad7.com` | Consulta |

**Cómo capturar:** `Win + Shift + S`, selecciona la ventana del navegador, clic en la notificación y
`Ctrl + S`. Guárdalas en **`dashboard/evidencias/`** en PNG, con el nombre **exacto** de cada paso
(si el nombre cambia, la imagen no aparece en `evidencias_actividad3.md`).

**Varias personas a la vez:** cada pestaña del navegador guarda su propia sesión. Para entrar con otra
persona abre una **pestaña nueva con `Ctrl + T` y escribe la dirección** (no uses "Duplicar pestaña",
porque copia la sesión). Así puedes tener a Ana, María, Pedro y José abiertos al mismo tiempo.

Dirección del dashboard: **http://127.0.0.1:8000/dashboard/**

Si la matriz no cabe completa en la ventana, baja el zoom del navegador a 80 % (`Ctrl` + `-`).

## 2. Pestaña de Ana: la matriz inicial (A3_E01)

1. Abre el dashboard y entra con `ana@actividad7.com`.
2. En el menú izquierdo, bajo **Administración**, pulsa **Roles y permisos**.

Debe verse exactamente esta tabla (en pantalla «sí» y «no»):

| Permiso | Administrador | Contador | Capturista | Consulta |
|---|---|---|---|---|
| Ver usuarios (`company.users.read`) | sí | sí | no | sí |
| Administrar usuarios (`company.users.write`) | sí | no | no | no |
| Ver cuentas (`accounts.read`) | sí | sí | sí | sí |
| Crear cuentas (`accounts.write`) | sí | sí | no | no |
| Ver conceptos (`concepts.read`) | sí | sí | sí | sí |
| Administrar conceptos (`concepts.write`) | sí | sí | no | no |
| Ver movimientos (`transactions.read`) | sí | sí | sí | sí |
| Registrar movimientos (`transactions.write`) | sí | sí | sí | no |
| Ver la matriz (`roles.read`) | sí | sí | no | no |
| Cambiar la matriz y asignar puestos (`roles.write`) | sí | no | no | no |

| # | Nombre del archivo | Qué debe verse |
|---|---|---|
| 1 | `A3_E01_matriz_inicial.png` | La matriz completa con los cinco grupos y la columna Administrador marcada "solo lectura". |

## 3. GraphiQL: la columna Capturista (A3_E02)

Abre una pestaña nueva en **http://127.0.0.1:8000/graphql**.

**a) Token de Ana.** Pega esto y ejecútalo:
```
mutation { login(input: { email: "ana@actividad7.com", password: "Secreto123!" }) { token } }
```
Copia el `token`. Abajo, en la pestaña **Headers**, pega (con tu token en lugar de `TOKEN`):
```
{ "Authorization": "Bearer TOKEN" }
```

**b) La consulta.** Borra lo anterior y pega:
```
query ListaDelRol($roleId: ID!) {
  rolePermissions(roleId: $roleId) {
    isActive
    permission {
      id
      code
    }
  }
}
```
En la pestaña **Variables** pega el contenido de `Actividad_5_Jesus_Uc/variables/u3a3_lista_capturista.json`
y ejecuta.

| # | Nombre del archivo | Qué debe verse |
|---|---|---|
| 2 | `A3_E02_graphiql_capturista.png` | La consulta, las Variables, el Header y la respuesta con **4** permisos: `accounts.read`, `concepts.read`, `transactions.read`, `transactions.write` (los mismos «sí» de la columna Capturista). |

## 4. Pestaña de María: Cuentas ANTES (A3_E04a)

1. Pestaña nueva (`Ctrl + T`), escribe la dirección del dashboard y entra con `maria@actividad7.com`.
2. En el menú pulsa **Cuentas**.

| # | Nombre del archivo | Qué debe verse |
|---|---|---|
| 3 | `A3_E04a_capturista_cuentas_antes.png` | "María · Capturista" arriba a la derecha y la tabla de Cuentas **sin** el botón Nueva cuenta. |

Deja esta pestaña abierta.

## 5. Pestaña de Pedro (sin captura todavía)

1. Pestaña nueva, dirección del dashboard, entra con `pedro@actividad7.com`.
2. Queda en **Resumen financiero**. Comprueba que arriba dice "Pedro · Consulta" y que **no** está el
   botón **Registrar movimiento**.

Deja esta pestaña abierta: se usa en el paso 10 con **la misma sesión** (el token dura 30 minutos;
haz los pasos 6 a 10 sin pausas largas).

## 6. Pestaña de Ana: la vista previa (A3_E03) y el guardado

1. Vuelve a la pestaña de Ana, en **Roles y permisos**.
2. En la columna **Capturista**, fila **Crear cuentas** (`accounts.write`), marca la casilla.
3. Arriba de la tabla aparece la **Vista previa · Capturista**.

| # | Nombre del archivo | Qué debe verse |
|---|---|---|
| 4 | `A3_E03_vista_previa.png` | Se van a activar `accounts.write`; se van a desactivar `ninguno`; sin cambio `4`; total final `5`; y la casilla de Capturista con "sí · se va a activar". |

4. Pulsa **Guardar columna**. Aparece el mensaje verde "Columna Capturista guardada (changed = true)…".

## 7. Pestaña de María: Cuentas DESPUÉS (A3_E04b)

1. Vuelve a la pestaña de María (no cierres sesión).
2. En el menú pulsa **Cuentas** (aunque ya estés ahí: al pulsarlo se vuelve a leer el rol).

| # | Nombre del archivo | Qué debe verse |
|---|---|---|
| 5 | `A3_E04b_capturista_cuentas_despues.png` | La misma pantalla de Cuentas, ahora **con** el botón Nueva cuenta. |

En esta misma pestaña toma también la captura del menú de la capturista:

| # | Nombre del archivo | Qué debe verse |
|---|---|---|
| 6 | `A3_E07b_capturista_sin_menu.png` | El menú izquierdo de María: Resumen financiero, Cuentas y Conceptos; **no** aparecen Usuarios ni Roles y permisos. |

## 8. Pestaña de José: el segundo capturista (A3_E04c)

1. Pestaña nueva, dirección del dashboard, entra con `jose@actividad7.com`.
2. En el menú pulsa **Cuentas**.

| # | Nombre del archivo | Qué debe verse |
|---|---|---|
| 7 | `A3_E04c_segundo_capturista.png` | "José · Capturista" arriba y el botón Nueva cuenta. Nadie editó su fila en Usuarios. |

## 9. Pestaña de Ana: segundo guardado (A3_E06) y cambio de puesto (A3_E05)

**Segundo guardado:**
1. En **Roles y permisos**, en el encabezado de la columna **Capturista**, pulsa **Revisar y guardar**.
   La vista previa dice: activar `ninguno`, desactivar `ninguno`, sin cambio `5`, total `5`.
2. Pulsa **Guardar columna**.

| # | Nombre del archivo | Qué debe verse |
|---|---|---|
| 8 | `A3_E06_segundo_guardado_changed_false.png` | El mensaje verde "La columna Capturista ya estaba así: setRolePermissions respondió changed = false. No se activó ni se desactivó nada y no se duplicaron filas…". |

**Cambio de puesto:**
3. En el menú pulsa **Usuarios**.
4. En la fila de **Pedro**, en la columna Rol, elige **Capturista** en el selector y pulsa **Guardar**
   (a la derecha del selector).

| # | Nombre del archivo | Qué debe verse |
|---|---|---|
| 9 | `A3_E05a_usuarios_cambio_de_puesto.png` | La fila de Pedro resaltada con Capturista, Administrador = No, y el mensaje verde "Pedro deja Consulta y toma Capturista… isAdmin sigue en No. La columna Consulta de la matriz no cambia…". |

5. En el menú pulsa **Roles y permisos**.

| # | Nombre del archivo | Qué debe verse |
|---|---|---|
| 10 | `A3_E05b_matriz_consulta_igual.png` | La columna **Consulta** igual que en la captura 1: sí, no, sí, no, sí, no, sí, no, no, no. (Capturista ya tiene «sí» en Crear cuentas.) |

## 10. Pestaña de Pedro: el mismo token ya puede registrar (A3_E08)

1. Vuelve a la pestaña de Pedro (la que abriste en el paso 5; **no** vuelvas a iniciar sesión).
2. En el menú pulsa **Resumen financiero**. Arriba ahora dice "Pedro · Capturista" y aparece el botón
   **Registrar movimiento**.
3. Pulsa **Registrar movimiento**. Cuenta `Banco`, concepto `Ingreso A7 (Ingreso)`, importe `150.00`,
   fecha la de hoy, descripción `Venta de mostrador`. Pulsa **Guardar**.

| # | Nombre del archivo | Qué debe verse |
|---|---|---|
| 11 | `A3_E08_pedro_mismo_token.png` | "Pedro · Capturista" arriba y el mensaje verde "Se registró el ingreso de 150.00 MXN en Banco (movimiento …)". |

Si la pestaña de Pedro te regresó al login (pasaron más de 30 minutos), entra otra vez con Pedro y
toma la captura igual; en `evidencias_actividad3.md` cambia "con la sesión que abrió siendo Consulta"
por "después del cambio de puesto".

## 11. Luis: la matriz en solo lectura (A3_E07a)

1. En la pestaña de Ana pulsa **Cerrar sesión** y entra con `luis@actividad7.com`.
2. En el menú pulsa **Roles y permisos**.

| # | Nombre del archivo | Qué debe verse |
|---|---|---|
| 12 | `A3_E07a_contador_solo_lectura.png` | El aviso ámbar "Solo lectura… tiene roles.read y no roles.write…", las casillas grises (deshabilitadas) y sin botones "Revisar y guardar". |

## 12. MySQL (A3_E09)

En otra terminal:
```
docker exec -it actividad4_mysql mysql -uactividad4 -pactividad4 actividad4_db
```
Pega estas tres consultas (están también en `Actividad_5_Jesus_Uc/comprobaciones_u3a3.sql`):
```
SELECT rp.id, p.code, rp.is_active FROM role_permissions rp JOIN roles r ON r.id = rp.role_id JOIN permissions p ON p.id = rp.permission_id WHERE r.code = 'CAPTURISTA' ORDER BY p.code;
SELECT role_id, permission_id, COUNT(*) AS veces FROM role_permissions GROUP BY role_id, permission_id HAVING COUNT(*) > 1;
SELECT u.name, r.code AS rol_activo, cu.is_admin FROM company_users cu JOIN users u ON u.id = cu.user_id LEFT JOIN company_user_roles cur ON cur.company_user_id = cu.id AND cur.is_active = 1 LEFT JOIN roles r ON r.id = cur.role_id JOIN companies c ON c.id = cu.company_id WHERE c.name = 'Empresa Balances A7' ORDER BY cu.id;
```

| # | Nombre del archivo | Qué debe verse |
|---|---|---|
| 13 | `A3_E09_mysql.png` | Capturista con 5 filas activas (incluye `accounts.write`), la segunda consulta con **Empty set** (sin parejas repetidas) y Pedro con un solo rol, CAPTURISTA, e `is_admin` 0. |

Sal de MySQL con `exit`.

## 13. Revisar

Abre `dashboard/evidencias_actividad3.md` en la vista previa de VS Code (`Ctrl + Shift + V`): deben
verse las 13 capturas sin imágenes rotas. Si alguna no la tomaste, borra su bloque de ese archivo.

## 14. Commit y push (rama `actividad3u3`)

El código ya está en la rama; este commit solo lleva las capturas. Desde la raíz del repositorio:

```
git add dashboard/evidencias dashboard/evidencias_actividad3.md
git commit -m "Unidad 3 Actividad 3: capturas de evidencias A3_E01 a A3_E09"
git push
```

Si `git status` muestra cambios en `Actividad_5_Jesus_Uc/variables/` (el script los regenera con los id
de tu base de datos), no los agregues.

## 15. ZIP y entrega

```
git archive --format=zip -o ../unidad3_actividad3_equipo.zip HEAD
```

El ZIP queda un nivel arriba del repositorio y no incluye `.env`, `node_modules`, ambientes virtuales
ni tokens. Entrega en Teams el enlace al repositorio (rama `actividad3u3`) y el ZIP
`unidad3_actividad3_equipo.zip`.
