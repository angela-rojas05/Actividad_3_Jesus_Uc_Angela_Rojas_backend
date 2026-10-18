-- =========================================================
-- Actividad 5 - Comprobaciones SQL
-- =========================================================

-- 1. Relaciones rol-permiso
SELECT rp.id          AS relacion_id,
       r.code         AS rol,
       p.code         AS permiso,
       rp.is_active   AS relacion_activa,
       p.is_active    AS permiso_activo
FROM role_permissions rp
JOIN roles r       ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
ORDER BY r.code, p.code;

-- 2. Duplicados (debe devolver cero filas)
SELECT role_id, permission_id, COUNT(*) AS veces
FROM role_permissions
GROUP BY role_id, permission_id
HAVING COUNT(*) > 1;

-- 3. Concesiones activas de CAPTURISTA
SELECT rp.id AS relacion_id, p.code AS permiso
FROM role_permissions rp
JOIN roles r       ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE r.code = 'CAPTURISTA'
  AND rp.is_active = 1
ORDER BY p.code;

-- 4. Conteos
SELECT COUNT(*) AS total_roles FROM roles;
SELECT COUNT(*) AS total_permissions FROM permissions;
SELECT COUNT(*) AS total_role_permissions FROM role_permissions;

-- 5. Estructura de role_permissions
SHOW CREATE TABLE role_permissions;

-- =========================================================
-- E06 - Preparación y restauración
-- =========================================================

-- Rol inactivo: preparar
UPDATE roles SET is_active = 0 WHERE code = 'CONSULTA';
-- Rol inactivo: restaurar
UPDATE roles SET is_active = 1 WHERE code = 'CONSULTA';

-- Permiso inactivo: preparar
UPDATE permissions SET is_active = 0 WHERE code = 'concepts.write';
-- Permiso inactivo: restaurar
UPDATE permissions SET is_active = 1 WHERE code = 'concepts.write';
