import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/Home.css';
import type { Trilha } from "../types/Trilha";
import { http } from "../lib/http";
import Layout from '../components/Layout';
import type { PaginationMeta } from "../types/Pagination";

function formatTrailStatus(status?: string | null, isCompleted?: boolean | null) {
  if (isCompleted) return "Concluída";
  if (!status) return "";
  const map: Record<string, string> = {
    COMPLETED: "Concluída",
    IN_PROGRESS: "Em andamento",
    ENROLLED: "Inscrito",
  };
  return map[status] ?? status;
}

const PAGE_SIZE = 8;

export default function Trails() {
  const [trilhas, setTrilhas] = useState<Trilha[]>([]);
  const [loadingTrilhas, setLoadingTrilhas] = useState(true);
  const [erroTrilhas, setErroTrilhas] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState<PaginationMeta | null>(null);
  const navigate = useNavigate();

  function handleMatricular(trail: Trilha) {
    navigate(`/trail-details/${trail.id}`);
  }

  useEffect(() => {
    let cancelled = false;

    async function getTrilhas(currentPage: number) {
      const response = await http.get("/trails/", {
        params: {
          page: currentPage,
          page_size: PAGE_SIZE,
        },
      });
      const { trails = [], pagination: meta } = response.data as {
        trails?: Trilha[];
        pagination?: PaginationMeta | null;
      };
      return { trails, pagination: meta ?? null };
    }

    (async () => {
      try {
        setLoadingTrilhas(true);
        const { trails: data, pagination: meta } = await getTrilhas(page);
        if (cancelled) return;
        setTrilhas(data ?? []);
        setPagination(meta);
        setErroTrilhas(null);
      } catch (e: any) {
        if (cancelled) return;
        setErroTrilhas(e?.detail || "Erro ao buscar trilhas.");
      } finally {
        if (cancelled) return;
        setLoadingTrilhas(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [page]);

  useEffect(() => {
    if (!pagination) return;
    if (pagination.pages > 0 && page > pagination.pages) {
      setPage(pagination.pages);
    }
  }, [pagination, page]);

  const totalPages = useMemo(
    () => Math.max(1, pagination?.pages ?? 1),
    [pagination?.pages]
  );

  // Garante que a página atual sempre seja válida se a lista mudar
  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  function goToPage(p: number) {
    const bounded = Math.min(Math.max(1, p), totalPages);
    setPage(bounded);
    // opcional: rolar a lista para o topo
    // document.querySelector('.tracks-grid')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // helper para montar lista de páginas (com elipses simples)
  function getPageList() {
    const pages: (number | '…')[] = [];
    const maxNumbers = 5; // quantos números mostrar no meio

    if (totalPages <= maxNumbers + 2) {
      // pequeno: mostra todas
      for (let i = 1; i <= totalPages; i++) pages.push(i);
      return pages;
    }

    const left = Math.max(2, page - 2);
    const right = Math.min(totalPages - 1, page + 2);

    pages.push(1);
    if (left > 2) pages.push('…');
    for (let i = left; i <= right; i++) pages.push(i);
    if (right < totalPages - 1) pages.push('…');
    pages.push(totalPages);

    return pages;
  }

  return (
    <Layout>
    <div>
      {loadingTrilhas && <p className="tracks-loading">Carregando trilhas…</p>}

      {erroTrilhas && !loadingTrilhas && (
        <div className="tracks-error" role="alert">
          {erroTrilhas}
        </div>
      )}

      {!loadingTrilhas && !erroTrilhas && trilhas.length === 0 && (
        <p className="tracks-empty">Nenhuma trilha disponível.</p>
      )}

      {!loadingTrilhas && !erroTrilhas && trilhas.length > 0 && (
        <>
          <div className="tracks-grid" style={{ paddingTop: 50 }}>
            {trilhas.map((t) => {
              const progressPercent = typeof t.progress_percent === "number"
                ? Math.round(t.progress_percent)
                : null;
              const statusLabel = formatTrailStatus(t.status, t.is_completed);
              const actionLabel = t.is_completed
                ? "Revisar"
                : t.nextAction ?? t.botaoLabel ?? "Continuar";

              return (
              <article key={t.id} className={`track-card ${t.is_completed ? "is-completed" : ""}`}>
              <div className="track-cover">
                <a href={`/trail-details/${t.id}`}>
                  <img src={t.thumbnail_url} alt={t.name} loading="lazy" />
                </a>
              </div>
                <div className="track-body">
                  <div className="track-rating" aria-label={`Avaliação ${t.review ?? 0} de 5`}>
                    {Array.from({ length: 5 }).map((_, idx) => (
                      <span
                        key={idx}
                        className={idx < (t.review ?? 0) ? "star filled" : "star"}
                      >
                        ★
                      </span>
                    ))}
                  </div>

                  <h3 className="track-title">{t.name}</h3>
                  {statusLabel && (
                    <span className={`track-status-badge status-${(t.status ?? "").toLowerCase()}`}>
                      {statusLabel}
                    </span>
                  )}
                  {progressPercent !== null && (
                    <div className="track-progress">
                      <div className="track-progress-bar">
                        <span style={{ width: `${progressPercent}%` }} />
                      </div>
                      <span className="track-progress-label">{progressPercent}%</span>
                    </div>
                  )}
                </div>

                <div className="track-footer">
                  <button
                    className="track-btn"
                    onClick={() => handleMatricular(t)}
                  >
                    {actionLabel}
                  </button>
                </div>
              </article>
              );
            })}
          </div>

          {/* Controles de paginação */}
          {totalPages > 1 && (
            <nav className="tracks-pagination" role="navigation" aria-label="Paginação de trilhas">
              <button
                className="page-btn"
                onClick={() => goToPage(1)}
                disabled={page === 1}
                aria-label="Primeira página"
              >
                «
              </button>
              <button
                className="page-btn"
                onClick={() => goToPage(page - 1)}
                disabled={page === 1}
                aria-label="Página anterior"
              >
                ‹
              </button>

              <ul className="page-list">
                {getPageList().map((p, idx) =>
                  p === '…' ? (
                    <li key={`ellipsis-${idx}`} className="page-ellipsis" aria-hidden>
                      …
                    </li>
                  ) : (
                    <li key={p}>
                      <button
                        className={`page-number ${p === page ? 'is-current' : ''}`}
                        onClick={() => goToPage(p)}
                        aria-current={p === page ? 'page' : undefined}
                        aria-label={`Ir para página ${p}`}
                      >
                        {p}
                      </button>
                    </li>
                  )
                )}
              </ul>

              <button
                className="page-btn"
                onClick={() => goToPage(page + 1)}
                disabled={page === totalPages}
                aria-label="Próxima página"
              >
                ›
              </button>
              <button
                className="page-btn"
                onClick={() => goToPage(totalPages)}
                disabled={page === totalPages}
                aria-label="Última página"
              >
                »
              </button>

              <span className="page-status" aria-live="polite">
                Página {page} de {totalPages}
              </span>
            </nav>
          )}
        </>
      )}
    </div>
    </Layout>
  );
}
