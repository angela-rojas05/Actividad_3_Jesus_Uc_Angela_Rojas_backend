# Investigación: configurar permisos con GraphQL

Sistema General de Ingresos · Unidad II · Actividad 5

## 1. Autenticación, autorización y configuración de permisos

La autenticación comprueba quién es una persona. En mi sistema es el inicio de sesión (`LoginInput` y `AuthPayload`). Ahí se revisan las credenciales. La autorización decide qué puede hacer esa persona después de identificarse. En `setRolePermissions`, la realiza `validar_acceso(db, actor, "roles.write")`, que revisa si la membresía tiene ese permiso. La configuración de permisos es diferente. Es decidir qué permisos tiene cada rol, y eso es lo que cambia `setRolePermissions`. La configuración cambia las reglas. La autorización las usa cuando alguien intenta hacer algo.

`actorCompanyUserId` no comprueba identidad porque es solo un número que el cliente escribe en las variables. El servidor verifica que esa membresía tenga el permiso. Sin embargo, junto con el ID no recibe ninguna credencial que demuestre que quien manda la petición es esa persona. Por ejemplo, cualquiera que escriba `"actor": "5"` actúa como Ana, la administradora. La documentación de Strawberry explica que comprobar la identidad no es responsabilidad de la librería. Eso corresponde al framework o al código propio. Los permisos se modelan aparte.

Lo hice así. En todas las pruebas usé a Ana como actor. Entendí que ese parámetro sirve para probar la autorización, no para garantizar seguridad real.

Source: Strawberry GraphQL, the Authentication and Permissions guides.

## 2. Variables, alias y fragmentos en pruebas repetibles

Cuando se escriben pruebas automatizadas, es común que ciertos valores, como identificadores de usuario, contraseñas o URLs, cambien entre entornos o incluso entre ejecuciones. En lugar de copiar estos valores en cada prueba, puedes usar variables. Así, si necesitas cambiar un valor, lo haces en un solo lugar.

Los alias te permiten guardar información de una respuesta o algún dato temporal para usarlo después. Por ejemplo, puedes guardar el resultado de una petición y usarlo en los siguientes pasos de la prueba. Esto hace que el código de tus pruebas sea más limpio y fácil de leer.

Los fragmentos de código o funciones reutilizables ayudan a evitar repetir lógica. Si necesitas realizar la misma acción varias veces, como iniciar sesión o crear un dato de prueba, define una función y úsala cuando la necesites. Esto reduce errores y facilita el mantenimiento de tus pruebas con el tiempo.

Una prueba que se puede repetir debe ejecutar la misma operación muchas veces con datos diferentes sin tener que escribirla de nuevo. Las variables lo hacen posible. Se escribe la operación una vez usando `$actor` y `$roleId`, y los valores se guardan en un archivo JSON aparte. Por eso, mi carpeta `variables/` tiene un archivo para cada caso (`e06_rol_inactivo.json`, `e08_vacia.json`) y los IDs reales se crean con un script. Los alias permiten pedir el mismo campo más de una vez en una sola petición sin que haya conflictos en la respuesta. En `ExplorarCatalogo` uso `cuentas` y `movimientos` para consultar dos recursos al mismo tiempo. Los fragmentos evitan repetir la lista de campos. `DatosPermiso` define `id`, `code` y `name` una sola vez y luego se reutiliza.

Mi propia operación junta las tres cosas y compara las listas de CAPTURISTA y CONSULTA:

```graphql
fragment DatosRelacion on RolePermission {
  id
  isActive
  permission {
    code
  }
}

query CompararRoles($actor: ID!, $capturista: ID!, $consulta: ID!) {
  capturista: rolePermissions(actorCompanyUserId: $actor, roleId: $capturista) {
    ...DatosRelacion
  }
  consulta: rolePermissions(actorCompanyUserId: $actor, roleId: $consulta) {
    ...DatosRelacion
  }
}
```

Variables:

```json
{
  "actor": "5",
  "capturista": "3",
  "consulta": "4"
}
```

Sin alias, los dos campos se llamarían `rolePermissions` y chocarían en la respuesta. Sin el fragmento tendría que copiar los campos dos veces. Con las variables puedo cambiar los roles sin tocar la consulta.

Lo hice así. Todas las capturas de la actividad salen de la misma operación, pero con archivos de variables diferentes. Esto permite repetirlas en otra base de datos si solo cambias los IDs.

Fuente: GraphQL Foundation, *Queries*.

## 3. Qué valida un enum o un input y qué sigue validando Python

Un enum o un input valida que el valor ingresado esté dentro de un conjunto de opciones permitidas. Por ejemplo, si tienes un enum para los días de la semana, solo acepta los valores lunes, martes, miércoles, jueves, viernes, sábado o domingo. Si el valor no está en esa lista, el enum marca un error.

Sin embargo, Python sigue validando otros aspectos. Por ejemplo, verifica que el tipo de dato sea correcto y que el código no tenga errores de sintaxis. También controla otros errores en tiempo de ejecución, como divisiones por cero o accesos a índices fuera de rango. Así, aunque un enum o un input filtra ciertos valores, Python sigue ejecutando sus propias reglas de validación durante la ejecución del programa.

Un enum y un input revisan la forma de los datos. Verifican que el valor esté en un conjunto permitido, que lleguen los campos obligatorios y que tengan el tipo correcto. Eso pasa antes de que mi código corra. En E02, el recurso `PAYMENTS` fue rechazado por GraphQL porque no está en el enum `PermissionResource`. La respuesta fue un error con `data: null`.

GraphQL no conoce las reglas del negocio. Por eso, Python sigue revisándolas. Verifica que el rol exista y esté activo, que no sea ADMINISTRADOR, que los permisos existan y estén activos, y que no haya IDs repetidos. En E06, todos esos casos pasaron la validación de tipos. Después, `validar_propuesta` los rechazó con mensajes como "El rol no existe." o "IDs de permiso repetidos".

`SetRolePermissionsInput` tiene el campo `permission_ids`, que en el esquema es `[ID!]!`. El signo de afuera exige que la lista no sea nula. El de adentro exige que ningún elemento sea nulo. Una lista vacía no tiene elementos. Por eso cumple las dos condiciones y GraphQL la acepta. En el sistema, `[]` tiene un significado concreto. Deja al rol sin permisos activos.

Lo hice así. En E08 envié `[]` a CAPTURISTA y quedó sin permisos activos. Sus filas se mantuvieron como inactivas.

Source: Strawberry GraphQL, Enums and Input types.

## 4. Atomicidad e idempotencia

Atomicidad significa que una operación ocurre por completo o no ocurre en absoluto. No hay estados intermedios. Si una parte de la operación falla, todo el proceso se revierte y el sistema vuelve al estado anterior. Esto es importante, por ejemplo, en transacciones bancarias, donde no se puede permitir que el dinero desaparezca o se duplique por un error.

La idempotencia significa que una operación se puede repetir varias veces y el resultado será el mismo que si se hubiera hecho una sola vez. Esto ayuda a evitar problemas cuando se repite una solicitud, como por errores de red. Por ejemplo, si un cliente envía el mismo pago dos veces, el sistema debe asegurarse de que solo se procese una vez.

La atomicidad significa que un cambio se aplica por completo o no se aplica en absoluto. La idempotencia significa que repetir la misma petición no cambia el resultado la segunda vez. Son cosas diferentes. Una trata sobre qué pasa si algo falla a la mitad, y la otra sobre qué pasa si se repite.

En `setRolePermissions`, `aplicar_plan` cambia las relaciones y hace `flush`. Después se hace un solo `commit`. Si algo falla, se hace `rollback`. La prueba E07 lo comprueba con una falla simulada antes del commit. La base queda igual. La idempotencia se ve en E04. Aplicar S1 por segunda vez devuelve `changed: false` sin altas ni bajas.

Enviar varias mutaciones en una petición no garantiza que se haga un rollback conjunto. GraphQL ejecuta los campos de una mutación uno tras otro. Cada resolver maneja su propia sesión y su propio commit. Si la segunda falla, la primera ya quedó guardada. Para lograr un rollback conjunto, hay que diseñar una sola mutación que haga todo en una transacción.

Lo hice de esta manera. Por eso, mi mutación recibe la lista completa del rol en un solo input. No activo ni desactivo permisos con mutaciones separadas.

Source: Strawberry GraphQL, 'Mutations'; GraphQL Foundation, 'Queries'.

## Fuentes consultadas

- GraphQL Foundation. *Queries*. https://graphql.org/learn/queries/ (consultado el 17 de octubre de 2026).
- Strawberry GraphQL. *Enums*. https://strawberry.rocks/docs/types/enums (consultado el 17 de octubre de 2026).
- Strawberry GraphQL. *Input types*. https://strawberry.rocks/docs/types/input-types (consultado el 17 de octubre de 2026).
- Strawberry GraphQL. *Mutations*. https://strawberry.rocks/docs/general/mutations (consultado el 17 de octubre de 2026).
