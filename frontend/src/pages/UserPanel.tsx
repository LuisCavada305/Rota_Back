import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import Avatar from "../components/Avatar";
import { http } from "../lib/http";
import { useAuth } from "../hooks/useAuth";
import "../styles/UserPanel.css";
import { BookOpen, Layers, Trophy } from "lucide-react";

type CertificateSummary = {
  hash: string;
  credential_id: string;
  issued_at?: string | null;
} | null;

type TrailProgress = {
  done: number;
  total: number;
  computed_progress_percent?: number | null;
  nextAction?: string | null;
  enrolledAt?: string | null;
  status?: string | null;
  completed_at?: string | null;
  certificate?: CertificateSummary;
};

type TrailOverview = {
  trail_id: number;
  name: string;
  thumbnail_url: string;
  author?: string | null;
  status?: string | null;
  progress: TrailProgress;
};

type OverviewSummary = {
  enrolled: number;
  active: number;
  completed: number;
};

type OverviewPayload = {
  summary: OverviewSummary;
  trails: TrailOverview[];
};

function normalizeStatus(status?: string | null) {
  return (status ?? "").toUpperCase();
}

export default function UserPanel() {
  const { user, loading: authLoading, logout } = useAuth();
  const [data, setData] = useState<OverviewPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const userId = user?.id;

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      if (authLoading) return;
      if (!user) {
        setLoading(false);
        setData(null);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const response = await http.get<OverviewPayload>("/user-trails/me/overview");
        if (!cancelled) {
          setData(response.data);
        }
      } catch (err: any) {
        if (!cancelled) {
          const message =
            err?.response?.data?.detail ??
            err?.message ??
            "Não foi possível carregar o painel agora.";
          setError(String(message));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [authLoading, userId]);

  const trails = data?.trails ?? [];

  const inProgress = useMemo(
    () =>
      trails.filter((trail) => normalizeStatus(trail.progress.status ?? trail.status) !== "COMPLETED"),
    [trails]
  );

  const completed = useMemo(
    () =>
      trails.filter((trail) => normalizeStatus(trail.progress.status ?? trail.status) === "COMPLETED"),
    [trails]
  );

  if (authLoading || loading) {
    return (
      <Layout>
        <section className="user-panel__feedback">
          <div className="user-panel__feedback-card">Carregando painel…</div>
        </section>
      </Layout>
    );
  }

  if (!user) {
    return (
      <Layout>
        <section className="user-panel__feedback">
          <div className="user-panel__feedback-card">
            <h2>Faça login para acessar o painel</h2>
            <p>Você precisa estar autenticado para visualizar seus cursos.</p>
            <Link to="/login" className="btn btn-primary">Entrar</Link>
          </div>
        </section>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <section className="user-panel__feedback">
          <div className="user-panel__feedback-card is-error">
            <h2>Não foi possível carregar o painel</h2>
            <p>{error}</p>
            <button type="button" className="btn btn-primary" onClick={() => window.location.reload()}>
              Tentar novamente
            </button>
          </div>
        </section>
      </Layout>
    );
  }

  const summary = data?.summary ?? { enrolled: 0, active: 0, completed: 0 };
  const firstName = user.username?.split(" ")[0] ?? user.username ?? "Visitante";

  return (
    <Layout>
      <section className="user-panel">
        <aside className="user-panel__sidebar">
          <nav className="user-panel__nav">
            <a className="user-panel__link is-active" href="#painel">
              Painel
            </a>
            <a className="user-panel__link" href="#enrolled">
              Cursos matriculados
            </a>
            <a className="user-panel__link" href="#completed">
              Cursos concluídos
            </a>
          </nav>
          <button
            type="button"
            className="user-panel__logout"
            onClick={() => { void logout(); }}
          >
            Sair
          </button>
        </aside>

        <main className="user-panel__main">
          <section className="user-panel__hero" id="painel">
            <Avatar name={user.username} email={user.email} src={user.profile_pic_url ?? undefined} size={72} />
            <div className="user-panel__hero-text">
              <span className="user-panel__hero-subtitle">Olá,</span>
              <h1 className="user-panel__hero-title">{firstName}</h1>
              <p className="user-panel__hero-note">Acompanhe o andamento das suas trilhas.</p>
            </div>
          </section>

          <section className="user-panel__summary" aria-label="Resumo de cursos">
            <article className="user-panel__stat-card">
              <div className="user-panel__stat-icon">
                <Layers size={22} />
              </div>
              <div className="user-panel__stat-value">{summary.enrolled}</div>
              <p className="user-panel__stat-label">Cursos inscritos</p>
            </article>
            <article className="user-panel__stat-card">
              <div className="user-panel__stat-icon user-panel__stat-icon--blue">
                <BookOpen size={22} />
              </div>
              <div className="user-panel__stat-value">{summary.active}</div>
              <p className="user-panel__stat-label">Cursos ativos</p>
            </article>
            <article className="user-panel__stat-card">
              <div className="user-panel__stat-icon user-panel__stat-icon--green">
                <Trophy size={22} />
              </div>
              <div className="user-panel__stat-value">{summary.completed}</div>
              <p className="user-panel__stat-label">Cursos concluídos</p>
            </article>
          </section>

          <section className="user-panel__section" id="enrolled">
            <header className="user-panel__section-header">
              <h2>Cursos em andamento</h2>
              {inProgress.length > 0 && (
                <span className="user-panel__section-count">{inProgress.length}</span>
              )}
            </header>
            {inProgress.length === 0 ? (
              <p className="user-panel__empty">Você ainda não possui trilhas em andamento.</p>
            ) : (
              <div className="user-panel__course-list">
                {inProgress.map((trail) => {
                  const pct = Math.round(
                    trail.progress.computed_progress_percent ??
                      (trail.progress.total > 0
                        ? (trail.progress.done / trail.progress.total) * 100
                        : 0)
                  );
                  return (
                    <article key={trail.trail_id} className="user-panel__course-card">
                      <img
                        src={trail.thumbnail_url}
                        alt={trail.name}
                        className="user-panel__course-thumb"
                        loading="lazy"
                      />
                      <div className="user-panel__course-body">
                        <h3>{trail.name}</h3>
                        <p className="user-panel__course-meta">
                          Lições concluídas: {trail.progress.done} de {trail.progress.total || 0}
                        </p>
                        <div className="user-panel__progress">
                          <div className="user-panel__progress-bar" aria-hidden="true">
                            <span style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} />
                          </div>
                          <span className="user-panel__progress-value">{pct}% completo</span>
                        </div>
                        <div className="user-panel__course-actions">
                          <Link to={`/trail-details/${trail.trail_id}`} className="btn btn-secondary btn-sm">
                            Continuar
                          </Link>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </section>

          <section className="user-panel__section" id="completed">
            <header className="user-panel__section-header">
              <h2>Cursos concluídos</h2>
              {completed.length > 0 && (
                <span className="user-panel__section-count">{completed.length}</span>
              )}
            </header>
            {completed.length === 0 ? (
              <p className="user-panel__empty">Nenhuma trilha concluída por enquanto.</p>
            ) : (
              <div className="user-panel__course-list">
                {completed.map((trail) => {
                  const completedAt = trail.progress.completed_at
                    ? new Date(trail.progress.completed_at).toLocaleDateString("pt-BR")
                    : null;
                  const certificate = trail.progress.certificate;
                  return (
                    <article key={trail.trail_id} className="user-panel__course-card">
                      <img
                        src={trail.thumbnail_url}
                        alt={trail.name}
                        className="user-panel__course-thumb"
                        loading="lazy"
                      />
                      <div className="user-panel__course-body">
                        <h3>{trail.name}</h3>
                        <p className="user-panel__course-meta">
                          {completedAt ? `Concluído em ${completedAt}` : "Concluído"}
                        </p>
                        <div className="user-panel__progress">
                          <div className="user-panel__progress-bar is-complete" aria-hidden="true">
                            <span style={{ width: "100%" }} />
                          </div>
                          <span className="user-panel__progress-value">100% completo</span>
                        </div>
                        <div className="user-panel__course-actions">
                          <Link to={`/trail-details/${trail.trail_id}`} className="btn btn-secondary btn-sm">
                            Revisar
                          </Link>
                          {certificate?.hash && (
                            <Link
                              to={`/certificados/?cert_hash=${certificate.hash}`}
                              className="btn btn-primary btn-sm"
                            >
                              Ver certificado
                            </Link>
                          )}
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        </main>
      </section>
    </Layout>
  );
}
