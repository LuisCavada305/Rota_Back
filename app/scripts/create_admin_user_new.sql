-- Cria (ou garante) um usuário administrador com credenciais conhecidas.
-- Email: rota.admin@rota.dev
-- Senha: NovaSenha!2025

WITH role_ids AS (
  SELECT
    (SELECT id FROM lk_role WHERE code = 'Admin') AS admin_role_id,
    (SELECT id FROM lk_sex WHERE code = 'N') AS default_sex_id
)
INSERT INTO users (
  email,
  password_hash,
  name_for_certificate,
  username,
  birthday,
  sex_id,
  role_id
)
SELECT
  'rota.admin@rota.dev',
  '$2b$12$g5ekeydOvZMUgT5SCv7O5uw6anX8e2Yb0GmyNI05Jn92f/B3U1lSy', -- hash gerado com bcrypt para NovaSenha!2025
  'Administrador ROTA',
  'rota_superadmin',
  DATE '1992-05-15',
  role_ids.default_sex_id,
  role_ids.admin_role_id
FROM role_ids
WHERE role_ids.admin_role_id IS NOT NULL
  AND role_ids.default_sex_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1
    FROM users
    WHERE email = 'rota.admin@rota.dev'
       OR username = 'rota_superadmin'
  );
