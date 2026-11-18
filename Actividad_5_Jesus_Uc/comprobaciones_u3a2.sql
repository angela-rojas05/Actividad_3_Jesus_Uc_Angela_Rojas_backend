-- =========================================================
-- Unidad III, Actividad 2 - Comprobaciones SQL
-- Ejecutar con:
--   docker exec -it actividad4_mysql mysql -uactividad4 -pactividad4 actividad4_db
-- =========================================================

-- 1. Idempotencia: una sola fila de movimiento por llave.
SELECT k.idempotency_key, k.transaction_id, t.amount, t.transaction_type, k.created_at
FROM idempotency_keys k
JOIN transactions t ON t.id = k.transaction_id
ORDER BY k.id;

-- 2. Llaves repetidas (debe devolver cero filas).
SELECT company_id, operation, idempotency_key, COUNT(*) AS veces
FROM idempotency_keys
GROUP BY company_id, operation, idempotency_key
HAVING COUNT(*) > 1;

-- 3. Movimientos de la prueba (debe haber 2: llave 1 y llave 2).
SELECT id, amount, short_description
FROM transactions
WHERE short_description = 'Pago de renta (prueba de idempotencia)';

-- 4. Membresías de la Empresa A con su rol (compárese con la tabla Usuarios).
--    Desactivar deja la fila con is_active = 0; no se borra.
SELECT cu.id, u.name, u.email, r.name AS rol, cu.is_admin, cu.is_active
FROM company_users cu
JOIN companies c ON c.id = cu.company_id
JOIN users u ON u.id = cu.user_id
LEFT JOIN company_user_roles cur ON cur.company_user_id = cu.id AND cur.is_active = 1
LEFT JOIN roles r ON r.id = cur.role_id
WHERE c.name = 'Empresa Balances A7'
ORDER BY cu.id;

-- 5. Cuentas de la Empresa A.
SELECT a.id, a.name, a.account_type, a.bank_name, a.is_active
FROM accounts a
JOIN companies c ON c.id = a.company_id
WHERE c.name = 'Empresa Balances A7'
ORDER BY a.id;

-- 6. Conceptos asignados por cuenta (Quitar deja is_active = 0).
SELECT a.name AS cuenta, co.name AS concepto, co.concept_type, ac.is_active
FROM account_concepts ac
JOIN accounts a  ON a.id = ac.account_id
JOIN concepts co ON co.id = ac.concept_id
JOIN companies c ON c.id = a.company_id
WHERE c.name = 'Empresa Balances A7'
ORDER BY a.name, co.name;
