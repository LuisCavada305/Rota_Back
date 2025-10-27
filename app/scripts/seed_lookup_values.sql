-- app/scripts/seed_lookup_values.sql
-- Popula as tabelas de lookup obrigatórias para o backend Flask da ROTA.
-- Execute após criar a estrutura do banco (migrada ou via SQLAlchemy).

-- Sexo / identidade de gênero
INSERT INTO lk_sex (code) VALUES
  ('MC'), -- ManCis
  ('MT'), -- ManTrans
  ('WC'), -- WomanCis
  ('WT'), -- WomanTrans
  ('OT'), -- Other
  ('NS')  -- NotSpecified
ON CONFLICT (code) DO NOTHING;

-- Cores / raça
INSERT INTO lk_color (code) VALUES
  ('BR'), -- Branco
  ('PR'), -- Preto
  ('PA'), -- Pardo
  ('AM'), -- Amarelo
  ('IN'), -- Indígena
  ('OU'), -- Outro
  ('NS')  -- Não especificado
ON CONFLICT (code) DO NOTHING;

-- Perfis de acesso
INSERT INTO lk_role (code) VALUES
  ('Admin'),
  ('User'),
  ('Manager')
ON CONFLICT (code) DO NOTHING;

-- Tipos de item de trilha
INSERT INTO lk_item_type (code) VALUES
  ('DOC'),
  ('VIDEO'),
  ('FORM')
ON CONFLICT (code) DO NOTHING;

-- Tipos de pergunta de formulário
INSERT INTO lk_question_type (code) VALUES
  ('ESSAY'),
  ('TRUE_OR_FALSE'),
  ('SINGLE_CHOICE')
ON CONFLICT (code) DO NOTHING;

-- Status de matrícula em trilhas
INSERT INTO lk_enrollment_status (code) VALUES
  ('ENROLLED'),
  ('IN_PROGRESS'),
  ('COMPLETED')
ON CONFLICT (code) DO NOTHING;

-- Status de progresso em itens
INSERT INTO lk_progress_status (code) VALUES
  ('NOT_STARTED'),
  ('IN_PROGRESS'),
  ('COMPLETED')
ON CONFLICT (code) DO NOTHING;

-- Opcional: garanta que as sequências estejam alinhadas com os registros atuais.
-- Por exemplo:
-- SELECT setval('lk_sex_id_seq',       (SELECT COALESCE(MAX(id), 1) FROM lk_sex));
-- SELECT setval('lk_color_id_seq',     (SELECT COALESCE(MAX(id), 1) FROM lk_color));
-- Ajuste conforme necessário para cada sequência criada automaticamente.

-- Índices de apoio (idempotentes para ambientes que reaplicam o seed)
CREATE INDEX IF NOT EXISTS idx_trails_created_date ON public.trails (created_date DESC);
CREATE INDEX IF NOT EXISTS idx_trails_name ON public.trails ("name");
CREATE INDEX IF NOT EXISTS idx_user_trails_user_status ON public.user_trails (user_id, status_id);
CREATE INDEX IF NOT EXISTS idx_trail_included_items_trail ON public.trail_included_items (trail_id, ord);
CREATE INDEX IF NOT EXISTS idx_trail_requirements_trail ON public.trail_requirements (trail_id, ord);
CREATE INDEX IF NOT EXISTS idx_trail_target_audience_trail ON public.trail_target_audience (trail_id, ord);
CREATE INDEX IF NOT EXISTS idx_user_item_progress_status ON public.user_item_progress (status_id);
