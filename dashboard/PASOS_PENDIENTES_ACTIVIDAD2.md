# Pasos pendientes — Unidad III, Actividad 2

El código ya está hecho, probado y subido a la rama `actividad2u3` (71 pruebas automáticas pasan y el
dashboard se probó en el navegador). Falta: **tomar 11 capturas, hacer el commit, hacer el push y
armar el ZIP.** Son unos 30 minutos.

## 0. Traer la rama

Desde la carpeta del repositorio:

```
git fetch origin
git switch actividad2u3
git pull
```

## 1. Levantar el proyecto

Abre Docker Desktop y espera a que termine de iniciar. En una terminal, desde `Actividad_5_Jesus_Uc/`
(si no tienes el archivo `.env`, créalo antes como dice el README de esa carpeta, sección "Configuración: JWT_SECRET"):

```
pip install -r requirements.txt
docker compose up -d
python scripts/preparar_demo_u3a2.py
uvicorn app.main:app
```

- `preparar_demo_u3a2.py` deja los datos como al inicio, y se puede correr las veces que haga falta.
  Si una captura sale mal, detén `uvicorn` (Ctrl + C), corre otra vez el script y vuelve a empezar
  desde la parte que falló.
- Deja esa terminal abierta mientras tomas las capturas.

Capturas: `Win + Shift + S`, selecciona la ventana del navegador, clic en la notificación y `Ctrl + S`.
Guárdalas en **`dashboard/evidencias/`** en PNG, con el nombre **exacto** de la tabla.

## 2. Parte 1: idempotencia en GraphiQL (capturas A2_E01 a A2_E05)

Abre **http://127.0.0.1:8000/graphql**.

**a) Token de Ana.** Pega esto y ejecútalo:
```
mutation { login(input: { email: "ana@actividad7.com", password: "Secreto123!" }) { token } }
```
Copia el `token`. Abajo, en la pestaña **Headers**, pega (con tu token en lugar de `TOKEN`):
```
{ "Authorization": "Bearer TOKEN" }
```

**b) La mutación.** Borra la consulta anterior y pega esta:
```
mutation CrearMovimiento($input: CreateTransactionInput!) {
  createTransaction(input: $input) {
    id
    amount
    transactionType
    transactionDate
    capturedAt
  }
}
```

**c) Los envíos.** En la pestaña **Variables** pega el contenido del archivo indicado y ejecuta.
Los archivos están en `Actividad_5_Jesus_Uc/variables/`. En cada captura deben verse las Variables
(con la `idempotencyKey`) y la respuesta.

| # | Nombre del archivo | Variables | Qué debe verse |
|---|---|---|---|
| 1 | `A2_E01_llave1_primer_envio.png` | `u3a2_tx_llave1.json` | Un `id` (anótalo), amount `100.00`. |
| 2 | `A2_E02_llave1_reintento_mismo_id.png` | `u3a2_tx_llave1.json` otra vez, sin cambiar nada | **El mismo `id`** y el mismo `capturedAt` que en la captura 1. |
| 3 | `A2_E03_llave2_otro_id.png` | `u3a2_tx_llave2.json` | Un `id` **distinto** aunque el monto sea igual. |
| 4 | `A2_E04_llave1_otro_monto_rechazado.png` | `u3a2_tx_llave1_otro_monto.json` | El error "Esa idempotencyKey ya se usó con otros datos…". |

Si el token vence (dura 30 minutos), repite el paso a).

**d) MySQL (captura 5).** En otra terminal:
```
docker exec -it actividad4_mysql mysql -uactividad4 -pactividad4 actividad4_db
```
Pega estas dos consultas:
```
SELECT k.idempotency_key, k.transaction_id, t.amount FROM idempotency_keys k JOIN transactions t ON t.id = k.transaction_id;
SELECT id, amount, short_description FROM transactions WHERE short_description = 'Pago de renta (prueba de idempotencia)';
```
| # | Nombre del archivo | Qué debe verse |
|---|---|---|
| 5 | `A2_E05_mysql_una_fila_por_llave.png` | Dos llaves y **dos** movimientos (no tres), con los id de las capturas 1 y 3. |

Sal de MySQL con `exit`.

## 3. Parte 2: dashboard administrativo (capturas A2_E06 a A2_E11)

Abre **http://127.0.0.1:8000/dashboard/** y entra con `ana@actividad7.com` / `Secreto123!`.
Hazlo **en este orden**, porque cada paso deja datos para la captura siguiente.

**Usuarios** (menú izquierdo → Administración → Usuarios):
1. Pulsa **Nuevo usuario**. Nombre `José Paz`, correo `jose.paz@actividad7.com`, contraseña `Secreto123!`. Guardar.
2. En la fila de José Paz pulsa **Desactivar**.
3. Pulsa otra vez **Nuevo usuario** y escribe Nombre `Luis Herrera`, correo `luis@actividad7.com`,
   contraseña `Secreto123!`. Guardar.

| # | Nombre del archivo | Cuándo | Qué debe verse |
|---|---|---|---|
| 6 | `A2_E06_usuarios.png` | Después del paso 2 | Conteos 4 activos / 1 administrador / 1 inactivo y José Paz como Inactivo. |
| 7 | `A2_E07_correo_duplicado.png` | Después del paso 3 | En el formulario, "No se guardó: El correo electrónico ya está registrado." |

Pulsa Cancelar para cerrar el formulario.

**Cuentas** (menú → Cuentas):
4. Pulsa **Nueva cuenta**. Nombre `Tarjeta empresarial`, tipo `Crédito`, banco `Santander`,
   CLABE `014180005555553333`, descripción `Gastos de oficina`. Guardar.

| # | Nombre del archivo | Cuándo | Qué debe verse |
|---|---|---|---|
| 8 | `A2_E08_cuentas.png` | Después del paso 4 | Banco, Caja, Ahorro y Tarjeta empresarial, con `****1234`, `****7788` y `****3333`. |

**Conceptos** (menú → Conceptos):
5. Pulsa **Nuevo concepto**. Nombre `Papelería`, tipo `Egreso`. Guardar.
6. A la derecha, en **Cuenta**, elige `Tarjeta empresarial`. En **Concepto a asignar** elige
   `Papelería (Egreso)` y pulsa **Asignar concepto**.
7. Pulsa **Asignar concepto** otra vez, sin cambiar nada.

| # | Nombre del archivo | Cuándo | Qué debe verse |
|---|---|---|---|
| 9 | `A2_E09_conceptos.png` | Después del paso 6 | Papelería en el catálogo y en la lista de la cuenta Tarjeta empresarial. |
| 10 | `A2_E10_concepto_ya_asignado.png` | Después del paso 7 | El aviso rojo "No se asignó: El concepto ya está asignado a la cuenta." |

8. (Sin captura) Pulsa **Quitar** junto a Papelería: desaparece de la cuenta y sigue en el catálogo.

**Solo consulta:**
9. Pulsa **Cerrar sesión** y entra con `pedro@actividad7.com` / `Secreto123!`. Ve a Usuarios.

| # | Nombre del archivo | Cuándo | Qué debe verse |
|---|---|---|---|
| 11 | `A2_E11_solo_consulta.png` | Después del paso 9 | "Pedro · Consulta" arriba, la tabla sin botón Nuevo usuario ni columna Acción. |

Revisa `dashboard/evidencias_actividad2.md` en la vista previa de VS Code (`Ctrl + Shift + V`): deben
verse las 11 capturas sin imágenes rotas. Si alguna no la tomaste, borra su sección de ese archivo.

## 4. Commit y push (rama `actividad2u3`)

El código ya está en la rama; este commit solo lleva las capturas. Desde la raíz del repositorio:

```
git add dashboard/evidencias dashboard/evidencias_actividad2.md
git commit -m "Unidad 3 Actividad 2: capturas de evidencias A2_E01 a A2_E11"
git push
```

Si `git status` muestra cambios en `Actividad_5_Jesus_Uc/variables/` (el script los regenera con los id
de tu base de datos), no los agregues.

## 5. ZIP y entrega

```
git archive --format=zip -o ../unidad3_actividad2_equipo.zip HEAD
```

El ZIP queda un nivel arriba del repositorio y no incluye `.env` ni tokens. Entrega en Teams el enlace
al repositorio (rama `actividad2u3`) y el ZIP.

## Opcional

- Si el profesor pide qué hizo cada quien, agrégalo en `dashboard/README.md` antes del commit.
- Para la demo final: `dashboard/guion_demo.md` es de la actividad 1; la parte administrativa se
  demuestra siguiendo la sección 3 de este archivo.
