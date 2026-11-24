-- =========================================================
-- Unidad III, Actividad 3 - Comprobaciones SQL
-- Ejecutar con:
--   docker exec -it actividad4_mysql mysql -uactividad4 -pactividad4 actividad4_db
-- =========================================================

-- 1. La matriz como se ve en la pantalla: 1 = «sí», 0 = «no».
--    Debe coincidir con la tabla de la sección 2.2 de la guía antes de cualquier cambio.
SELECT p.code AS permiso,
       MAX(CASE WHEN r.code = 'ADMINISTRADOR' AND rp.is_active = 1 THEN 1 ELSE 0 END) AS administrador,
       MAX(CASE WHEN r.code = 'CONTADOR'      AND rp.is_active = 1 THEN 1 ELSE 0 END) AS contador,
       MAX(CASE WHEN r.code = 'CAPTURISTA'    AND rp.is_active = 1 THEN 1 ELSE 0 END) AS capturista,
       MAX(CASE WHEN r.code = 'CONSULTA'      AND rp.is_active = 1 THEN 1 ELSE 0 END) AS consulta
FROM permissions p
LEFT JOIN role_permissions rp ON rp.permission_id = p.id
LEFT JOIN roles r ON r.id = rp.role_id
WHERE p.is_active = 1
GROUP BY p.id, p.code
ORDER BY p.id;

-- 2. La columna Capturista, fila por fila (también las inactivas: quitar no borra).
SELECT rp.id, p.code, rp.is_active
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE r.code = 'CAPTURISTA'
ORDER BY p.code;

-- 3. Parejas (rol, permiso) repetidas: debe devolver cero filas aunque se guarde dos veces.
SELECT role_id, permission_id, COUNT(*) AS veces
FROM role_permissions
GROUP BY role_id, permission_id
HAVING COUNT(*) > 1;

-- 4. El puesto de cada persona de la Empresa A: un solo rol activo, isAdmin sin cambios.
SELECT u.name, u.email, r.code AS rol_activo, cu.is_admin,
       (SELECT COUNT(*) FROM company_user_roles x
         WHERE x.company_user_id = cu.id AND x.is_active = 1) AS roles_activos
FROM company_users cu
JOIN companies c ON c.id = cu.company_id
JOIN users u ON u.id = cu.user_id
LEFT JOIN company_user_roles cur ON cur.company_user_id = cu.id AND cur.is_active = 1
LEFT JOIN roles r ON r.id = cur.role_id
WHERE c.name = 'Empresa Balances A7'
ORDER BY cu.id;

-- 5. Historial del puesto de Pedro: la fila anterior queda inactiva, no se borra.
SELECT cur.id, r.code, cur.is_active
FROM company_user_roles cur
JOIN roles r ON r.id = cur.role_id
JOIN company_users cu ON cu.id = cur.company_user_id
JOIN users u ON u.id = cu.user_id
WHERE u.email = 'pedro@actividad7.com'
ORDER BY cur.id;
