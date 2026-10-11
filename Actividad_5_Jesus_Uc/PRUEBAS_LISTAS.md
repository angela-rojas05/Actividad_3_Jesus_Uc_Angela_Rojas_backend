# PRUEBAS_LISTAS.md - Guía de Ejecución y Evidencias de Capturas

Guía paso a paso para ejecutar las pruebas en **GraphiQL** (`http://127.0.0.1:8000/graphql`) y consola de **MySQL**, con los **identificadores reales ya inyectados** (sin placeholders) e indicaciones detalladas de **cómo y dónde tomar cada captura de pantalla**.

---

## 📌 Guía General para la Toma de Capturas

1. **Dónde se toman**:
   - **Puntos 1 al 9**: En tu navegador web en la interfaz interactiva de **GraphiQL** (`http://127.0.0.1:8000/graphql`).
   - **Puntos 10 y 11**: En tu terminal de consola (**PowerShell** o CMD) ejecutando los comandos de Docker y MySQL.
2. **Cómo encuadrar en GraphiQL**:
   - Pega la operación en el **panel izquierdo**.
   - Haz clic en el botón de **Play / Ejecutar (▶)** en la barra superior.
   - Toma la captura abarcando **ambos paneles al mismo tiempo**:
     - **Panel izquierdo**: La consulta o mutación visible con sus argumentos.
     - **Panel derecho**: La respuesta JSON resultante (`"data"` con status exitoso o `"errors"` con el mensaje de rechazo).
3. **Herramienta rápida en Windows**: Usa la combinación de teclas `Win + Shift + S` para seleccionar el área deseada.

---

### 🔑 Identificadores de la sesión preparada:
- **Empresa**: ID `7` (`Empresa Demo Roles 678398`, Tax ID: `EDR678398`)
- **Admin Principal**: Membresía ID `12` (`admin_678398@demoroles.com`)
- **Contador**: Membresía ID `13` (`contador_678398@demoroles.com`)
- **Capturista**: Membresía ID `14` (`capturista_678398@demoroles.com`)
- **Consulta**: Membresía ID `15` (`consulta_678398@demoroles.com`)
- **Cuenta Financiera**: ID `2` (`Cuenta Operativa BBVA`)
- **Concepto Financiero**: ID `1` (`Venta de Servicios` - INCOME)
- **Roles del Sistema**: ADMINISTRADOR (`1`), CONTADOR (`2`), CAPTURISTA (`3`), CONSULTA (`4`)

---

## 1. Consulta de Roles y Permisos (4 roles y 10 permisos)
> **Regla que demuestra**: *Demuestra que el catálogo base de roles y permisos fue sembrado correctamente y está accesible para consulta.*

- **📸 Dónde capturar**: En GraphiQL (`http://127.0.0.1:8000/graphql`).
- **👁️ Qué debe verse**: En el panel izquierdo la query `ObtenerRolesYPermisos`; en el panel derecho los 4 roles (`ADMINISTRADOR`, `CONTADOR`, `CAPTURISTA`, `CONSULTA`) y los 10 permisos con sus descripciones.
- **📁 Nombre de evidencia sugerido**: `01_roles_y_permisos.png`

```graphql
query ObtenerRolesYPermisos {
  roles(actorCompanyUserId: "12") {
    id
    code
    name
    description
    isActive
  }
  permissions(actorCompanyUserId: "12") {
    id
    code
    name
    description
    isActive
  }
}
```

---

## 2. Permisos Asignados a CAPTURISTA y CONSULTA
> **Regla que demuestra**: *Demuestra que la matriz asigna 4 permisos operativos a Capturista y 4 permisos de solo lectura a Consulta.*

- **📸 Dónde capturar**: En GraphiQL.
- **👁️ Qué debe verse**: Panel izquierdo con `PermisosCapturistaYConsulta`; panel derecho mostrando 4 permisos para Capturista (`accounts.read`, `concepts.read`, `transactions.read`, `transactions.write`) y 4 para Consulta (`company.users.read`, `accounts.read`, `concepts.read`, `transactions.read`).
- **📁 Nombre de evidencia sugerido**: `02_permisos_capturista_consulta.png`

```graphql
query PermisosCapturistaYConsulta {
  permisosCapturista: rolePermissions(
    actorCompanyUserId: "12"
    roleId: "3"
  ) {
    id
    role {
      code
    }
    permission {
      code
      name
    }
    isActive
  }
  permisosConsulta: rolePermissions(
    actorCompanyUserId: "12"
    roleId: "4"
  ) {
    id
    role {
      code
    }
    permission {
      code
      name
    }
    isActive
  }
}
```

---

## 3. Registrar Transacción con CAPTURISTA (Resultado: Éxito)
> **Regla que demuestra**: *Demuestra que el rol CAPTURISTA posee el permiso transactions.write para registrar movimientos.*

- **📸 Dónde capturar**: En GraphiQL.
- **👁️ Qué debe verse**: Panel izquierdo con `actorCompanyUserId: "14"` y el input del movimiento; panel derecho con `"data"` mostrando la transacción creada con `amount: "18500.00"`, `capturedBy` y `isActive: true`.
- **📁 Nombre de evidencia sugerido**: `03_create_transaction_capturista_ok.png`

```graphql
mutation RegistrarTransaccionCapturista {
  createTransaction(
    actorCompanyUserId: "14"
    input: {
      accountId: "2"
      conceptId: "1"
      transactionType: INCOME
      amount: "18500.00"
      shortDescription: "Cobro de factura A-501 por Capturista"
    }
  ) {
    id
    amount
    transactionType
    capturedBy
    shortDescription
    isActive
  }
}
```

---

## 4. Registrar Transacción con CONSULTA (Resultado: Error esperado)
> **Regla que demuestra**: *Demuestra que el rol CONSULTA carece de transactions.write y la operación es denegada con GraphQLError sin escribir nada.*

- **📸 Dónde capturar**: En GraphiQL.
- **👁️ Qué debe verse**: Panel izquierdo con `actorCompanyUserId: "15"`; panel derecho con bloque `"errors"` conteniendo el mensaje `"El rol no tiene el permiso transactions.write"` y `"data": null`.
- **📁 Nombre de evidencia sugerido**: `04_create_transaction_consulta_denegado.png`

```graphql
mutation RegistrarTransaccionConsultaRechazada {
  createTransaction(
    actorCompanyUserId: "15"
    input: {
      accountId: "2"
      conceptId: "1"
      transactionType: INCOME
      amount: "5000.00"
      shortDescription: "Intento no autorizado de registro"
    }
  ) {
    id
    amount
  }
}
```

---

## 5. Crear Cuenta con CONTADOR (Resultado: Éxito)
> **Regla que demuestra**: *Demuestra que el rol CONTADOR tiene accounts.write para registrar cuentas financieras de su empresa.*

- **📸 Dónde capturar**: En GraphiQL.
- **👁️ Qué debe verse**: Panel izquierdo con `actorCompanyUserId: "13"` creando la cuenta "Caja Chica Operaciones"; panel derecho con `"data"` mostrando el nuevo `id` y `isActive: true`.
- **📁 Nombre de evidencia sugerido**: `05_create_account_contador_ok.png`

```graphql
mutation CrearCuentaConContador {
  createAccount(
    actorCompanyUserId: "13"
    input: {
      companyId: "7"
      accountType: CASH
      name: "Caja Chica Operaciones"
      shortDescription: "Fondo fijo de efectivo para gastos menores"
    }
  ) {
    id
    name
    accountType
    isActive
  }
}
```

---

## 6. Crear Cuenta con CAPTURISTA (Resultado: Error esperado)
> **Regla que demuestra**: *Demuestra que el rol CAPTURISTA no tiene accounts.write y el sistema bloquea la creación de cuentas.*

- **📸 Dónde capturar**: En GraphiQL.
- **👁️ Qué debe verse**: Panel izquierdo con `actorCompanyUserId: "14"`; panel derecho mostrando `"errors": [{"message": "El rol no tiene el permiso accounts.write"}]` y `"data": null`.
- **📁 Nombre de evidencia sugerido**: `06_create_account_capturista_denegado.png`

```graphql
mutation CrearCuentaConCapturistaRechazado {
  createAccount(
    actorCompanyUserId: "14"
    input: {
      companyId: "7"
      accountType: SAVINGS
      name: "Cuenta Bloqueada Capturista"
      shortDescription: "No debe crearse"
    }
  ) {
    id
    name
  }
}
```

---

## 7. Promover CAPTURISTA a CONTADOR (assignRole con Admin)
> **Regla que demuestra**: *Demuestra que el admin puede reasignar roles desactivando el rol previo y dejando activo el nuevo rol CONTADOR.*

- **📸 Dónde capturar**: En GraphiQL.
- **👁️ Qué debe verse**: Panel izquierdo con `actorCompanyUserId: "12"` ejecutando `assignRole` sobre `companyUserId: "14"` con `roleId: "2"`; panel derecho mostrando la reasignación activa al rol `CONTADOR`.
- **📁 Nombre de evidencia sugerido**: `07_assign_role_capturista_a_contador.png`

```graphql
mutation PromoverCapturistaAContador {
  assignRole(
    actorCompanyUserId: "12"
    input: {
      companyUserId: "14"
      roleId: "2"
    }
  ) {
    id
    companyUser {
      id
    }
    role {
      id
      code
      name
    }
    isActive
  }
}
```

---

## 8. Crear Cuenta con el Usuario Promovido (Resultado: Éxito)
> **Regla que demuestra**: *Demuestra que al cambiar el rol a CONTADOR, el usuario adquiere inmediatamente los permisos de accounts.write.*

- **📸 Dónde capturar**: En GraphiQL.
- **👁️ Qué debe verse**: Panel izquierdo con `actorCompanyUserId: "14"` (mismo usuario que fue rechazado en el paso 6); panel derecho con `"data"` mostrando la cuenta creada satisfactoriamente.
- **📁 Nombre de evidencia sugerido**: `08_create_account_usuario_promovido_ok.png`

```graphql
mutation CrearCuentaConUsuarioPromovido {
  createAccount(
    actorCompanyUserId: "14"
    input: {
      companyId: "7"
      accountType: SAVINGS
      name: "Cuenta Inversiones Ahora Permitida"
      shortDescription: "Creada por Camilo tras ser promovido a CONTADOR"
    }
  ) {
    id
    name
    accountType
    isActive
  }
}
```

---

## 9. Segundo createCompanyAdmin en la Misma Empresa (Resultado: Error esperado)
> **Regla que demuestra**: *Demuestra la regla de negocio que restringe a un único administrador principal activo por empresa.*

- **📸 Dónde capturar**: En GraphiQL.
- **👁️ Qué debe verse**: Panel izquierdo intentando crear otro admin en `companyId: "7"`; panel derecho mostrando `"errors": [{"message": "La empresa ya tiene un administrador principal."}]`.
- **📁 Nombre de evidencia sugerido**: `09_segundo_admin_rechazado.png`

```graphql
mutation SegundoAdminFalla {
  createCompanyAdmin(
    input: {
      companyId: "7"
      name: "Segundo Administrador"
      email: "admin2_678398@demoroles.com"
      password: "Password123."
    }
  ) {
    id
    isAdmin
  }
}
```

---

## 10. Consultas de Verificación en MySQL (Consola)
> **Regla que demuestra**: *Demuestra la persistencia física en MySQL de los catálogos, la matriz relacional y las transacciones registradas.*

- **📸 Dónde capturar**: En tu **Terminal / PowerShell**.
- **👁️ Qué debe verse**: La ventana de la consola completa donde se lea el comando ejecutado y la tabla de resultados que arroja MySQL.
- **📁 Nombre de evidencia sugerido**: `10_verificacion_mysql.png` (o separada en `10a_roles_mysql.png`, `10b_matriz_mysql.png`, `10c_transactions_mysql.png`)

### 10.1. Listar roles y permisos del sistema:
```powershell
docker exec actividad4_mysql mysql -uactividad4 -pactividad4 actividad4_db -e "SELECT id, code, name, is_active FROM roles; SELECT id, code, name FROM permissions;"
```

### 10.2. Matriz de roles y permisos asignados:
```powershell
docker exec actividad4_mysql mysql -uactividad4 -pactividad4 actividad4_db -e "SELECT r.code AS rol, p.code AS permiso, rp.is_active FROM roles r JOIN role_permissions rp ON r.id = rp.role_id JOIN permissions p ON p.id = rp.permission_id ORDER BY r.id, p.code;"
```

### 10.3. Listar transacciones registradas (con LEFT JOIN a usuarios):
```powershell
docker exec actividad4_mysql mysql -uactividad4 -pactividad4 actividad4_db -e "SELECT * FROM transactions; SELECT t.id, t.account_id, t.concept_id, t.transaction_type, t.amount, t.captured_by, u.email AS capturado_por_email, t.is_active FROM transactions t LEFT JOIN users u ON t.captured_by = u.id;"
```

---

## 11. Idempotencia y Reinicio del Servidor
> **Regla que demuestra**: *Demuestra que reiniciar uvicorn no duplica filas de seed en MySQL.*

- **📸 Dónde capturar**: En tu **Terminal / PowerShell**.
- **👁️ Qué debe verse**: El comando con el conteo antes del reinicio (4 roles), el reinicio del servidor en la otra terminal o log de uvicorn, y el conteo posterior en MySQL mostrando que sigue exactamente en 4 roles.
- **📁 Nombre de evidencia sugerido**: `11_idempotencia_reinicio.png`

### Paso 1: Conteo actual
```powershell
docker exec actividad4_mysql mysql -uactividad4 -pactividad4 actividad4_db -e "SELECT COUNT(*) AS total_roles FROM roles;"
```

### Paso 2: Reiniciar uvicorn
En la terminal donde corre uvicorn, presiona `Ctrl + C` y vuelve a ejecutar:
```powershell
uvicorn app.main:app --reload
```

### Paso 3: Conteo posterior
```powershell
docker exec actividad4_mysql mysql -uactividad4 -pactividad4 actividad4_db -e "SELECT COUNT(*) AS total_roles FROM roles;"
```
*(El conteo debe permanecer inalterado en 4 roles)*
