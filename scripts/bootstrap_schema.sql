-- app/scripts/bootstrap_schema.sql
-- Script completo para criar o schema PostgreSQL utilizado pelo backend ROTA.
-- Execute em um banco vazio (ou após `DROP SCHEMA public CASCADE` caso queira recriar).

-- DROP SCHEMA public;

CREATE SCHEMA public AUTHORIZATION pg_database_owner;

-- ===== Tipos personalizados ==================================================

-- DROP TYPE public."item_type";
CREATE TYPE public."item_type" AS ENUM ('VIDEO', 'DOC', 'FORM');

-- DROP TYPE public."question_type";
CREATE TYPE public."question_type" AS ENUM ('ESSAY', 'TRUE_OR_FALSE', 'SINGLE_CHOICE');

-- DROP TYPE public."roles_enum";
CREATE TYPE public."roles_enum" AS ENUM ('Admin', 'User', 'Manager');

-- DROP TYPE public."sex_type";
CREATE TYPE public."sex_type" AS ENUM ('M', 'F', 'O', 'N');

-- ===== Sequências ============================================================

-- DROP SEQUENCE public.form_answers_id_seq;
CREATE SEQUENCE public.form_answers_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.form_question_id_seq;
CREATE SEQUENCE public.form_question_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.form_question_options_id_seq;
CREATE SEQUENCE public.form_question_options_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.form_submissions_id_seq;
CREATE SEQUENCE public.form_submissions_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.forms_id_seq;
CREATE SEQUENCE public.forms_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.forum_posts_id_seq;
CREATE SEQUENCE public.forum_posts_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.forum_topics_id_seq;
CREATE SEQUENCE public.forum_topics_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.forums_id_seq;
CREATE SEQUENCE public.forums_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.lk_color_id_seq;
CREATE SEQUENCE public.lk_color_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.lk_enrollment_status_id_seq;
CREATE SEQUENCE public.lk_enrollment_status_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.lk_item_type_id_seq;
CREATE SEQUENCE public.lk_item_type_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.lk_progress_status_id_seq;
CREATE SEQUENCE public.lk_progress_status_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.lk_question_type_id_seq;
CREATE SEQUENCE public.lk_question_type_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.lk_role_id_seq;
CREATE SEQUENCE public.lk_role_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.lk_sex_id_seq;
CREATE SEQUENCE public.lk_sex_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.trail_certificates_id_seq;
CREATE SEQUENCE public.trail_certificates_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.trail_included_items_id_seq;
CREATE SEQUENCE public.trail_included_items_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.trail_requirements_id_seq;
CREATE SEQUENCE public.trail_requirements_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.trail_sections_id_seq;
CREATE SEQUENCE public.trail_sections_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.trail_target_audience_id_seq;
CREATE SEQUENCE public.trail_target_audience_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.trails_id_seq;
CREATE SEQUENCE public.trails_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.user_item_progress_id_seq;
CREATE SEQUENCE public.user_item_progress_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.user_trails_id_seq;
CREATE SEQUENCE public.user_trails_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.users_user_id_seq;
CREATE SEQUENCE public.users_user_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- DROP SEQUENCE public.videos_id_seq;
CREATE SEQUENCE public.videos_id_seq START 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- ===== Tabelas de lookup =====================================================

-- DROP TABLE public.lk_color;
CREATE TABLE public.lk_color (
    id  SERIAL PRIMARY KEY,
    code VARCHAR(8) NOT NULL UNIQUE
);

-- DROP TABLE public.lk_enrollment_status;
CREATE TABLE public.lk_enrollment_status (
    id   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE
);

-- DROP TABLE public.lk_item_type;
CREATE TABLE public.lk_item_type (
    id   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE
);

-- DROP TABLE public.lk_progress_status;
CREATE TABLE public.lk_progress_status (
    id   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE
);

-- DROP TABLE public.lk_question_type;
CREATE TABLE public.lk_question_type (
    id   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE
);

-- DROP TABLE public.lk_role;
CREATE TABLE public.lk_role (
    id   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE
);

-- DROP TABLE public.lk_sex;
CREATE TABLE public.lk_sex (
    id   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(8) NOT NULL UNIQUE
);

-- ===== Tabelas principais ====================================================

-- DROP TABLE public.users;
CREATE TABLE public.users (
    user_id             BIGSERIAL PRIMARY KEY,
    sex                 public."sex_type",
    password_hash       TEXT NOT NULL,
    created_at          TIMESTAMPTZ,
    email               VARCHAR NOT NULL UNIQUE,
    birthday            DATE NOT NULL,
    name_for_certificate TEXT NOT NULL,
    username            TEXT UNIQUE,
    social_name         VARCHAR,
    "role"              public."roles_enum" NOT NULL DEFAULT 'User',
    profile_pic_url     TEXT,
    banner_pic_url      TEXT,
    role_id             INT REFERENCES public.lk_role(id),
    sex_id              INT REFERENCES public.lk_sex(id),
    created_at_utc      TIMESTAMP,
    color_id            INT NOT NULL REFERENCES public.lk_color(id)
);

-- DROP TABLE public.trails;
CREATE TABLE public.trails (
    id              BIGSERIAL PRIMARY KEY,
    thumbnail_url   TEXT NOT NULL,
    "name"          TEXT NOT NULL,
    review          NUMERIC,
    review_count    INT,
    created_date    DATE,
    created_by      BIGINT REFERENCES public.users(user_id) ON DELETE SET NULL ON UPDATE CASCADE,
    author          TEXT,
    description     TEXT,
    requirements    TEXT[],
    target_audience TEXT[],
    included_items  TEXT[]
);
CREATE INDEX idx_trails_created_date ON public.trails (created_date DESC);
CREATE INDEX idx_trails_name ON public.trails ("name");

-- DROP TABLE public.user_trails;
CREATE TABLE public.user_trails (
    id                 BIGSERIAL PRIMARY KEY,
    user_id            BIGINT REFERENCES public.users(user_id) ON DELETE CASCADE,
    trail_id           BIGINT REFERENCES public.trails(id) ON DELETE CASCADE,
    status_id          INT REFERENCES public.lk_enrollment_status(id),
    progress_percent   NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    started_at         TIMESTAMPTZ,
    completed_at       TIMESTAMPTZ,
    started_at_utc     TIMESTAMP,
    completed_at_utc   TIMESTAMP,
    review_rating      SMALLINT CHECK (review_rating IS NULL OR (review_rating >= 1 AND review_rating <= 5)),
    review_comment     TEXT,
    reviewed_at        TIMESTAMPTZ,
    CONSTRAINT ck_ut_progress CHECK (progress_percent >= 0.00 AND progress_percent <= 100.00),
    CONSTRAINT user_trails_unique UNIQUE (user_id, trail_id)
);
CREATE INDEX idx_user_trails_user ON public.user_trails (user_id);
CREATE INDEX idx_user_trails_trail ON public.user_trails (trail_id);
CREATE INDEX idx_user_trails_user_status ON public.user_trails (user_id, status_id);

-- DROP TABLE public.forums;
CREATE TABLE public.forums (
    id          SERIAL PRIMARY KEY,
    slug        VARCHAR(128) NOT NULL UNIQUE,
    title       VARCHAR(255) NOT NULL,
    description TEXT,
    is_general  BOOLEAN NOT NULL,
    trail_id    INT UNIQUE REFERENCES public.trails(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- DROP TABLE public.trail_certificates;
CREATE TABLE public.trail_certificates (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    trail_id         BIGINT NOT NULL REFERENCES public.trails(id) ON DELETE CASCADE,
    certificate_hash VARCHAR(64) NOT NULL UNIQUE,
    credential_id    VARCHAR(64) NOT NULL UNIQUE,
    issued_at        TIMESTAMPTZ NOT NULL,
    issued_at_utc    TIMESTAMP NOT NULL,
    CONSTRAINT uq_trail_certificates_user_trail UNIQUE (user_id, trail_id)
);
CREATE INDEX idx_trail_certificates_user ON public.trail_certificates (user_id);
CREATE INDEX idx_trail_certificates_trail ON public.trail_certificates (trail_id);

-- DROP TABLE public.trail_included_items;
CREATE TABLE public.trail_included_items (
    id       BIGSERIAL PRIMARY KEY,
    trail_id BIGINT NOT NULL REFERENCES public.trails(id) ON DELETE CASCADE,
    text_val VARCHAR(500) NOT NULL,
    ord      INT NOT NULL DEFAULT 0
);
CREATE INDEX idx_trail_included_items_trail ON public.trail_included_items (trail_id, ord);

-- DROP TABLE public.trail_requirements;
CREATE TABLE public.trail_requirements (
    id       BIGSERIAL PRIMARY KEY,
    trail_id BIGINT NOT NULL REFERENCES public.trails(id) ON DELETE CASCADE,
    text_val VARCHAR(500) NOT NULL,
    ord      INT NOT NULL DEFAULT 0
);
CREATE INDEX idx_trail_requirements_trail ON public.trail_requirements (trail_id, ord);

-- DROP TABLE public.trail_sections;
CREATE TABLE public.trail_sections (
    id          BIGSERIAL PRIMARY KEY,
    trail_id    BIGINT NOT NULL REFERENCES public.trails(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    description TEXT,
    order_index INT NOT NULL DEFAULT 0,
    CONSTRAINT ck_trail_sections_order_nonneg CHECK (order_index >= 0),
    CONSTRAINT uq_trail_sections_trail_order UNIQUE (trail_id, order_index)
);
CREATE INDEX idx_trail_sections_trail ON public.trail_sections (trail_id);
CREATE INDEX idx_trail_sections_trail_order ON public.trail_sections (trail_id, order_index);

-- DROP TABLE public.trail_target_audience;
CREATE TABLE public.trail_target_audience (
    id       BIGSERIAL PRIMARY KEY,
    trail_id BIGINT NOT NULL REFERENCES public.trails(id) ON DELETE CASCADE,
    text_val VARCHAR(500) NOT NULL,
    ord      INT NOT NULL DEFAULT 0
);
CREATE INDEX idx_trail_target_audience_trail ON public.trail_target_audience (trail_id, ord);

-- DROP TABLE public.forum_topics;
CREATE TABLE public.forum_topics (
    id            SERIAL PRIMARY KEY,
    forum_id      INT NOT NULL REFERENCES public.forums(id) ON DELETE CASCADE,
    title         VARCHAR(255) NOT NULL,
    created_by_id INT REFERENCES public.users(user_id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_forum_topics_forum_id ON public.forum_topics (forum_id);

-- DROP TABLE public.trail_items;
CREATE TABLE public.trail_items (
    id                     BIGINT DEFAULT nextval('videos_id_seq') PRIMARY KEY,
    url                    TEXT NOT NULL,
    order_index            INT DEFAULT 0,
    trail_id               BIGINT NOT NULL REFERENCES public.trails(id) ON DELETE CASCADE ON UPDATE CASCADE,
    "type"                 public."item_type" NOT NULL,
    title                  TEXT,
    duration_seconds       INT,
    item_type_id           INT REFERENCES public.lk_item_type(id),
    section_id             BIGINT REFERENCES public.trail_sections(id) ON DELETE SET NULL,
    requires_completion    BOOLEAN,
    requires_completion_yn VARCHAR(1),
    CONSTRAINT ck_trail_items_order_nonneg CHECK (order_index >= 0),
    CONSTRAINT videos_unique UNIQUE (url)
);
CREATE INDEX idx_trail_items_trail_id ON public.trail_items (trail_id);
CREATE INDEX idx_trail_items_section ON public.trail_items (section_id);
CREATE INDEX idx_trail_items_type ON public.trail_items (item_type_id);
CREATE INDEX idx_trail_items_trail_order ON public.trail_items (trail_id, order_index);
CREATE INDEX idx_trail_items_trail_section_order ON public.trail_items (trail_id, section_id, order_index);
CREATE UNIQUE INDEX trail_items_section_order_unique ON public.trail_items (section_id, order_index) WHERE section_id IS NOT NULL;
CREATE UNIQUE INDEX trail_items_trail_order_legacy_unique ON public.trail_items (trail_id, order_index) WHERE section_id IS NULL;

-- DROP TABLE public.user_item_progress;
CREATE TABLE public.user_item_progress (
    id                       BIGSERIAL PRIMARY KEY,
    user_id                  BIGINT REFERENCES public.users(user_id) ON DELETE CASCADE,
    trail_item_id            BIGINT REFERENCES public.trail_items(id) ON DELETE CASCADE,
    status_id                INT REFERENCES public.lk_progress_status(id),
    progress_value           INT,
    last_interaction         TIMESTAMPTZ,
    completed_at             TIMESTAMPTZ,
    last_interaction_utc     TIMESTAMP,
    completed_at_utc         TIMESTAMP,
    last_passed_submission_id BIGINT,
    CONSTRAINT user_item_progress_unique UNIQUE (user_id, trail_item_id)
);
CREATE INDEX idx_uip_user ON public.user_item_progress (user_id);
CREATE INDEX idx_uip_item ON public.user_item_progress (trail_item_id);
CREATE INDEX idx_user_item_progress_user_trail ON public.user_item_progress (user_id, trail_item_id);
CREATE INDEX idx_user_item_progress_status ON public.user_item_progress (status_id);

-- DROP TABLE public.forms;
CREATE TABLE public.forms (
    id                     BIGSERIAL PRIMARY KEY,
    trail_item_id          BIGINT REFERENCES public.trail_items(id) ON DELETE CASCADE,
    title                  TEXT,
    description            TEXT,
    min_score_to_pass      NUMERIC(5,2) NOT NULL DEFAULT 70.00,
    randomize_questions    BOOLEAN,
    randomize_questions_yn BPCHAR(1),
    CONSTRAINT ck_forms_random CHECK (randomize_questions_yn = ANY(ARRAY['S','N'])),
    CONSTRAINT forms_trail_item_uk UNIQUE (trail_item_id)
);
CREATE INDEX idx_forms_trail_item ON public.forms (trail_item_id);

-- DROP TABLE public.forum_posts;
CREATE TABLE public.forum_posts (
    id            SERIAL PRIMARY KEY,
    topic_id      INT NOT NULL REFERENCES public.forum_topics(id) ON DELETE CASCADE,
    author_id     INT REFERENCES public.users(user_id) ON DELETE SET NULL,
    "content"     TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    parent_post_id INT REFERENCES public.forum_posts(id) ON DELETE CASCADE
);
CREATE INDEX ix_forum_posts_topic_id ON public.forum_posts (topic_id);
CREATE INDEX ix_forum_posts_parent_post_id ON public.forum_posts (parent_post_id);

-- DROP TABLE public.form_question;
CREATE TABLE public.form_question (
    id             BIGSERIAL PRIMARY KEY,
    form_id        BIGINT REFERENCES public.forms(id) ON DELETE CASCADE,
    prompt         TEXT,
    question_type_id INT REFERENCES public.lk_question_type(id),
    required       BOOLEAN,
    required_yn    BPCHAR(1),
    order_index    INT NOT NULL DEFAULT 0,
    points         NUMERIC(6,2) NOT NULL DEFAULT 1.00,
    CONSTRAINT ck_fq_required CHECK (required_yn = ANY(ARRAY['Y','N'])),
    CONSTRAINT form_question_order_unique UNIQUE (form_id, order_index)
);
CREATE INDEX idx_form_question_form ON public.form_question (form_id);

-- DROP TABLE public.form_question_options;
CREATE TABLE public.form_question_options (
    id            BIGSERIAL PRIMARY KEY,
    question_id   BIGINT REFERENCES public.form_question(id) ON DELETE CASCADE,
    option_text   TEXT,
    is_correct    BOOLEAN,
    is_correct_yn BPCHAR(1),
    order_index   INT NOT NULL DEFAULT 0,
    CONSTRAINT ck_fqo_correct CHECK (is_correct_yn = ANY(ARRAY['Y','N']))
);
CREATE INDEX idx_fqo_question ON public.form_question_options (question_id);

-- DROP TABLE public.form_submissions;
CREATE TABLE public.form_submissions (
    id                BIGSERIAL PRIMARY KEY,
    form_id           BIGINT REFERENCES public.forms(id) ON DELETE CASCADE,
    user_id           BIGINT REFERENCES public.users(user_id) ON DELETE CASCADE,
    submitted_at      TIMESTAMPTZ,
    submitted_at_utc  TIMESTAMP,
    score             NUMERIC(6,2) NOT NULL DEFAULT 0.00,
    passed            BOOLEAN,
    passed_yn         BPCHAR(1),
    duration_seconds  INT,
    CONSTRAINT ck_fs_passed CHECK (passed_yn = ANY(ARRAY['Y','N']))
);
CREATE INDEX idx_fs_form ON public.form_submissions (form_id);
CREATE INDEX idx_fs_user ON public.form_submissions (user_id);

-- DROP TABLE public.form_answers;
CREATE TABLE public.form_answers (
    id                 BIGSERIAL PRIMARY KEY,
    submission_id      BIGINT REFERENCES public.form_submissions(id) ON DELETE CASCADE,
    question_id        BIGINT REFERENCES public.form_question(id) ON DELETE CASCADE,
    selected_option_id BIGINT REFERENCES public.form_question_options(id) ON DELETE SET NULL,
    answer_text        TEXT,
    is_correct         BOOLEAN,
    is_correct_yn      BPCHAR(1),
    points_awarded     NUMERIC(6,2),
    CONSTRAINT ck_fa_correct CHECK (is_correct_yn = ANY(ARRAY['Y','N']) OR is_correct_yn IS NULL),
    CONSTRAINT form_answers_unique UNIQUE (submission_id, question_id)
);
CREATE INDEX fa_submission_idx ON public.form_answers (submission_id);
CREATE INDEX fa_question_idx ON public.form_answers (question_id);

-- ===== Funções e gatilhos ====================================================

-- DROP FUNCTION public.fn_check_item_section_same_trail();
CREATE OR REPLACE FUNCTION public.fn_check_item_section_same_trail()
RETURNS trigger
LANGUAGE plpgsql AS $function$
DECLARE
  sec_trail_id BIGINT;
BEGIN
  IF NEW.section_id IS NULL THEN
    RETURN NEW;
  END IF;

  SELECT ts.trail_id INTO sec_trail_id
  FROM public.trail_sections ts
  WHERE ts.id = NEW.section_id;

  IF sec_trail_id IS NULL THEN
    RAISE EXCEPTION 'Section % não encontrada', NEW.section_id USING ERRCODE = 'foreign_key_violation';
  END IF;

  IF NEW.trail_id <> sec_trail_id THEN
    RAISE EXCEPTION 'trail_items.trail_id (%) difere de trail_sections.trail_id (%) para section_id=%',
      NEW.trail_id, sec_trail_id, NEW.section_id
      USING ERRCODE = 'check_violation';
  END IF;

  RETURN NEW;
END;
$function$;

-- DROP TRIGGER trg_check_item_section_same_trail ON public.trail_items;
CREATE TRIGGER trg_check_item_section_same_trail
BEFORE INSERT OR UPDATE OF section_id, trail_id
ON public.trail_items
FOR EACH ROW
EXECUTE FUNCTION public.fn_check_item_section_same_trail();

-- ===== Views =================================================================

CREATE OR REPLACE VIEW public.v_section_stats AS
SELECT
    ts.id AS section_id,
    ts.trail_id,
    ts.title AS section_title,
    COUNT(ti.id) AS items_count,
    SUM(CASE WHEN it.code = 'VIDEO' THEN 1 ELSE 0 END) AS videos_count,
    SUM(CASE WHEN it.code = 'DOC'   THEN 1 ELSE 0 END) AS docs_count,
    SUM(CASE WHEN it.code = 'FORM'  THEN 1 ELSE 0 END) AS forms_count
FROM public.trail_sections ts
LEFT JOIN public.trail_items ti ON ti.section_id = ts.id
LEFT JOIN public.lk_item_type it ON it.id = ti.item_type_id
GROUP BY ts.id, ts.trail_id, ts.title;

CREATE OR REPLACE VIEW public.v_trail_stats AS
SELECT
    t.id   AS trail_id,
    t.name AS trail_name,
    COUNT(ti.id) AS items_count,
    SUM(CASE WHEN it.code = 'VIDEO' THEN 1 ELSE 0 END) AS videos_count,
    SUM(CASE WHEN it.code = 'DOC'   THEN 1 ELSE 0 END) AS docs_count,
    SUM(CASE WHEN it.code = 'FORM'  THEN 1 ELSE 0 END) AS forms_count
FROM public.trails t
LEFT JOIN public.trail_items ti ON ti.trail_id = t.id
LEFT JOIN public.lk_item_type it ON it.id = ti.item_type_id
GROUP BY t.id, t.name;

CREATE OR REPLACE VIEW public.v_user_section_progress AS
WITH items AS (
    SELECT ti.section_id, COUNT(*) AS total_items
    FROM public.trail_items ti
    WHERE ti.section_id IS NOT NULL
    GROUP BY ti.section_id
),
done AS (
    SELECT uip.user_id, ti.section_id, COUNT(*) AS completed_items
    FROM public.user_item_progress uip
    JOIN public.trail_items ti ON ti.id = uip.trail_item_id
    JOIN public.lk_progress_status ps ON ps.id = uip.status_id
    WHERE ti.section_id IS NOT NULL AND ps.code = 'COMPLETED'
    GROUP BY uip.user_id, ti.section_id
)
SELECT
    ut.user_id,
    ts.trail_id,
    ts.id AS section_id,
    CASE
        WHEN i.total_items IS NULL OR i.total_items = 0 THEN 0.00
        ELSE ROUND(100.0 * COALESCE(d.completed_items, 0)::NUMERIC / i.total_items::NUMERIC, 2)
    END AS computed_progress_percent
FROM public.user_trails ut
JOIN public.trail_sections ts ON ts.trail_id = ut.trail_id
LEFT JOIN items i ON i.section_id = ts.id
LEFT JOIN done d ON d.user_id = ut.user_id AND d.section_id = ts.id;

CREATE OR REPLACE VIEW public.v_user_trail_progress AS
WITH items AS (
    SELECT trail_items.trail_id, COUNT(*) AS total_items
    FROM public.trail_items
    GROUP BY trail_items.trail_id
),
done AS (
    SELECT uip.user_id, ti.trail_id, COUNT(*) AS completed_items
    FROM public.user_item_progress uip
    JOIN public.trail_items ti ON ti.id = uip.trail_item_id
    JOIN public.lk_progress_status ps ON ps.id = uip.status_id
    WHERE ps.code = 'COMPLETED'
    GROUP BY uip.user_id, ti.trail_id
)
SELECT
    ut.user_id,
    ut.trail_id,
    CASE
        WHEN i.total_items IS NULL OR i.total_items = 0 THEN 0.00
        ELSE ROUND(100.0 * COALESCE(d.completed_items, 0)::NUMERIC / i.total_items::NUMERIC, 2)
    END AS computed_progress_percent
FROM public.user_trails ut
LEFT JOIN items i ON i.trail_id = ut.trail_id
LEFT JOIN done d ON d.user_id = ut.user_id AND d.trail_id = ut.trail_id;

-- Fim
