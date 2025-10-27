import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import { useAuth } from "../hooks/useAuth";
import { http } from "../lib/http";
import "../styles/Profile.css";

type ProfileData = {
  username: string;
  name_for_certificate: string;
  social_name?: string | null;
};

type ProfileResponse = {
  profile: ProfileData;
};

function normalizeError(err: unknown): string {
  if (typeof err === "string") return err;
  if (err && typeof err === "object") {
    const maybeAxios = err as { response?: { data?: any } };
    const detail = maybeAxios.response?.data?.detail;
    if (Array.isArray(detail) && detail[0]?.msg) {
      return String(detail[0].msg);
    }
    if (typeof detail === "string") {
      return detail;
    }
    const message = (err as { message?: string }).message;
    if (message) return message;
  }
  return "Não foi possível completar a operação.";
}

export default function Profile() {
  const { user, loading: authLoading } = useAuth();
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [nameInput, setNameInput] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [justSaved, setJustSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadProfile() {
      if (authLoading) return;
      if (!user) {
        setLoading(false);
        setProfile(null);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const { data } = await http.get<ProfileResponse>("/me/profile");
        if (cancelled) return;
        setProfile(data.profile);
        setNameInput(data.profile.name_for_certificate);
      } catch (err) {
        if (!cancelled) {
          setError(normalizeError(err));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void loadProfile();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user]);

  useEffect(() => {
    if (!editMode) return;
    setFormError(null);
    setJustSaved(false);
    setNameInput(profile?.name_for_certificate ?? "");
  }, [editMode, profile]);

  const certificateName = useMemo(
    () => profile?.name_for_certificate ?? "—",
    [profile?.name_for_certificate]
  );

  if (authLoading || loading) {
    return (
      <Layout>
        <section className="profile-feedback">
          <div className="profile-feedback-card">Carregando perfil…</div>
        </section>
      </Layout>
    );
  }

  if (!user) {
    return (
      <Layout>
        <section className="profile-feedback">
          <div className="profile-feedback-card">
            <h2>Entre para ver seu perfil</h2>
            <p>Faça login para visualizar ou atualizar o nome impresso nos certificados.</p>
            <Link to="/login" className="profile-btn profile-btn--primary">Entrar</Link>
          </div>
        </section>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <section className="profile-feedback">
          <div className="profile-feedback-card is-error">
            <h2>Não foi possível carregar os dados</h2>
            <p>{error}</p>
            <button
              type="button"
              className="profile-btn profile-btn--primary"
              onClick={() => window.location.reload()}
            >
              Tentar novamente
            </button>
          </div>
        </section>
      </Layout>
    );
  }

  if (!profile) {
    return (
      <Layout>
        <section className="profile-feedback">
          <div className="profile-feedback-card">Nenhum dado de perfil encontrado.</div>
        </section>
      </Layout>
    );
  }

  const startEdit = () => {
    setJustSaved(false);
    setFormError(null);
    setNameInput(profile.name_for_certificate);
    setEditMode(true);
  };

  const cancelEdit = () => {
    setEditMode(false);
    setFormError(null);
    setNameInput(profile.name_for_certificate);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = nameInput.trim();
    if (!trimmed) {
      setFormError("Informe um nome para o certificado.");
      return;
    }
    setSaving(true);
    setFormError(null);
    setJustSaved(false);
    try {
      const { data } = await http.patch<ProfileResponse>("/me/profile", {
        name_for_certificate: trimmed,
      });
      setProfile(data.profile);
      setNameInput(data.profile.name_for_certificate);
      setEditMode(false);
      setJustSaved(true);
    } catch (err) {
      setFormError(normalizeError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout>
      <section className="profile-page">
        <div className="profile-card">
          <header className="profile-card__header">
            <div>
              <h1>Detalhes</h1>
              <p>Gerencie o nome exibido nos seus certificados.</p>
            </div>
            {!editMode && (
              <button
                type="button"
                className="profile-btn"
                onClick={startEdit}
              >
                Editar
              </button>
            )}
          </header>

          {!editMode ? (
            <dl className="profile-fields">
              <div className="profile-field">
                <dt>Nome para emissão do certificado</dt>
                <dd>{certificateName}</dd>
              </div>
              <div className="profile-field">
                <dt>Usuário</dt>
                <dd>{profile.username}</dd>
              </div>
            </dl>
          ) : (
            <form className="profile-form" onSubmit={handleSubmit}>
              <div className="profile-form__group">
                <label htmlFor="certificateName">Nome para emissão do certificado</label>
                <input
                  id="certificateName"
                  name="certificateName"
                  type="text"
                  value={nameInput}
                  onChange={(event) => setNameInput(event.target.value)}
                  autoComplete="name"
                  maxLength={150}
                  required
                />
                <span className="profile-field-help">Este nome aparecerá exatamente assim no certificado.</span>
              </div>

              <div className="profile-form__group">
                <label htmlFor="username">Usuário</label>
                <input
                  id="username"
                  name="username"
                  type="text"
                  value={profile.username}
                  readOnly
                  disabled
                />
                <span className="profile-field-help">Não é possível alterar seu usuário por aqui.</span>
              </div>

              {formError && (
                <div className="profile-form__error" role="alert">
                  {formError}
                </div>
              )}

              <div className="profile-form__actions">
                <button
                  type="button"
                  className="profile-btn profile-btn--ghost"
                  onClick={cancelEdit}
                  disabled={saving}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="profile-btn profile-btn--primary"
                  disabled={saving}
                >
                  {saving ? "Salvando…" : "Salvar alterações"}
                </button>
              </div>
            </form>
          )}

          {justSaved && !editMode && (
            <div className="profile-success" role="status">
              Nome do certificado atualizado com sucesso!
            </div>
          )}
        </div>
      </section>
    </Layout>
  );
}
