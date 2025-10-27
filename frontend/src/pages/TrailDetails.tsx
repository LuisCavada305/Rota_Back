import Layout from "../components/Layout";
import "../styles/TrailDetails.css";
import { http } from "../lib/http";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { normalizePaginatedPayload, type PaginatedPayload } from "../types/Pagination";

type SectionItem = {
  id: number;
  title: string;
  duration_seconds?: number | null;
};

type Section = {
  id: number;
  title: string;
  order_index?: number;
  items: SectionItem[];
};

type SectionSummary = Omit<Section, "items">;

type TrailCore = {
  id: number;
  name: string;                // no back está "name"; no front eu exponho como "title"
  thumbnail_url: string;
  description?: string | null;
  author?: string | null;
  category?: string | null;
  review?: number | null;
  review_count?: number | null;
  user_review_rating?: number | null;
  user_review_comment?: string | null;
};

type TextValRow = { text_val: string };

type CertificateSummary = {
  hash: string;
  credential_id: string;
  issued_at?: string | null;
} | null;

type Progress = {
  done: number;
  total: number;
  nextAction?: string;
  enrolledAt?: string; // ISO
  pct?: number;        // calculado/fallback
  status?: string | null;
  completed_at?: string | null;
  certificate?: CertificateSummary;
  reviewRating?: number | null;
  reviewComment?: string | null;
};

function secondsToMMSS(total?: number | null) {
  if (!total || total <= 0) return undefined;
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function formatStatusLabel(status?: string | null) {
  if (!status) return "";
  const map: Record<string, string> = {
    COMPLETED: "Concluída",
    IN_PROGRESS: "Em andamento",
    ENROLLED: "Inscrito",
  };
  return map[status] ?? status;
}

export default function TrailDetails() {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [enrolling, setEnrolling] = useState(false);
  const [enrollError, setEnrollError] = useState<string | null>(null);
  const [certLoading, setCertLoading] = useState(false);
  const [certError, setCertError] = useState<string | null>(null);
  const [shareOpen, setShareOpen] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const shareMenuRef = useRef<HTMLDivElement | null>(null);
  const [hoverRating, setHoverRating] = useState<number | null>(null);
  const [reviewSaving, setReviewSaving] = useState(false);
  const [reviewFeedback, setReviewFeedback] = useState<{ message: string; kind: "success" | "error" } | null>(null);
  const navigate = useNavigate();

  // "View model" final que a UI consome
  const [vm, setVm] = useState<{
    id: number;
    title: string;
    category: string;
    thumbnail_url: string;
    description: string;
    learn: string[];         // você pode usar para “O que você aprenderá?” ou esconder se vier vazio
    sections: Section[];
    instructor: { name: string; initials: string };
    includes: string[];
    requirements: string[];
    audience: string[];
    progress: Progress;
    nextLessonDate?: string; // dd/mm/aaaa (apenas exibição)
    ratingAverage: number | null;
    ratingCount: number;
  } | null>(null);

  useEffect(() => {
    let mounted = true;
    async function fetchAll() {
      if (!id) return;
      setLoading(true);
      setErr(null);

      try {
        // 1) núcleo da trilha
        const pCore = http.get<TrailCore>(`/trails/${id}`).then(r => r.data);

        // 2) sections + items (tente o “com itens”, se 404 cai para /sections e depois busca items por seção)
        const pSectionsWithItems = http
          .get<Section[]>(`/trails/${id}/sections-with-items`)
          .then(r => r.data)
          .catch(async () => {
            const sections: SectionSummary[] = [];
            const sectionPageSize = 50;

            let secPage = 1;
            // fallback: busca sections paginadas e, em seguida, items por seção
            while (true) {
              const response = await http.get(`/trails/${id}/sections`, {
                params: { page: secPage, page_size: sectionPageSize },
              });
              const { data: chunk, pagination } = normalizePaginatedPayload<"sections", SectionSummary>(
                response.data as PaginatedPayload<"sections", SectionSummary>,
                "sections"
              );
              sections.push(...chunk);
              if (!pagination || pagination.pages === 0 || secPage >= pagination.pages) {
                break;
              }
              secPage += 1;
            }

            const itemsBySec = await Promise.all(
              sections.map(async (sec) => {
                const items: SectionItem[] = [];
                const itemPageSize = 50;
                let itemPage = 1;

                while (true) {
                  const response = await http.get(`/trails/${id}/sections/${sec.id}/items`, {
                    params: { page: itemPage, page_size: itemPageSize },
                  });
                  const { data: chunk, pagination } = normalizePaginatedPayload<"items", SectionItem>(
                    response.data as PaginatedPayload<"items", SectionItem>,
                    "items"
                  );
                  items.push(...chunk);
                  if (!pagination || pagination.pages === 0 || itemPage >= pagination.pages) {
                    break;
                  }
                  itemPage += 1;
                }

                return { ...sec, items };
              })
            );

            return itemsBySec;
          });

        // 3) listas (podem existir ou não)
        const pIncluded = http
          .get<TextValRow[]>(`/trails/${id}/included-items`)
          .then(r => r.data.map(x => x.text_val))
          .catch(() => [] as string[]);

        const pReqs = http
          .get<TextValRow[]>(`/trails/${id}/requirements`)
          .then(r => r.data.map(x => x.text_val))
          .catch(() => [] as string[]);

        const pAudience = http
          .get<TextValRow[]>(`/trails/${id}/audience`)
          .then(r => r.data.map(x => x.text_val))
          .catch(() => [] as string[]);

        // 4) progresso do usuário nessa trilha
        const pProgress = http
          .get<Partial<Progress> & {
            computed_progress_percent?: number;
            started_at?: string;
            certificate?: { hash: string; credential_id: string; issued_at?: string | null } | null;
            review_rating?: number | null;
            review_comment?: string | null;
          }>(
            `/user-trails/${id}/progress`
          )
          .then(r => r.data as Partial<Progress> & {
            computed_progress_percent?: number;
            started_at?: string;
            certificate?: { hash: string; credential_id: string; issued_at?: string | null } | null;
            review_rating?: number | null;
            review_comment?: string | null;
          })
          .catch(() => ({}) as Partial<Progress> & {
            computed_progress_percent?: number;
            started_at?: string;
            certificate?: { hash: string; credential_id: string; issued_at?: string | null } | null;
            review_rating?: number | null;
            review_comment?: string | null;
          });

        // 5) pegar “aprendizados” (se existir; senão usamos vazio)
        const pLearn = http
          .get<TextValRow[]>(`/trails/${id}/learn`) // se você criar essa rota
          .then(r => r.data.map(x => x.text_val))
          .catch(() => [] as string[]);

        const [core, sections, includes, reqs, audience, progressRaw, learn] = await Promise.all([
          pCore,
          pSectionsWithItems,
          pIncluded,
          pReqs,
          pAudience,
          pProgress,
          pLearn,
        ]);

        // Normalizações e fallbacks
        const title = core.name ?? "Trilha";
        const category = core.category ?? "Curso";
        const description = core.description ?? "";
        const instructorName = core.author || "Projeto Rota";
        const initials =
          instructorName
            .split(" ")
            .map(s => s[0])
            .filter(Boolean)
            .join("")
            .slice(0, 2)
            .toUpperCase() || "PR";

        // Ordena sections e items
        const orderedSections = [...sections]
          .sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0))
          .map(sec => ({
            ...sec,
            items: [...(sec.items || [])].sort((a, b) => (a.title || "").localeCompare(b.title || "")),
          }));

        // Progress fallback
        const done = typeof progressRaw?.done === "number" ? progressRaw.done : 0;
        // total pode vir do back; se não vier, calculamos com base no total de items
        const total =
          typeof progressRaw?.total === "number"
            ? progressRaw.total
            : orderedSections.reduce((acc, s) => acc + (s.items?.length || 0), 0);
        const pctFromBack =
          typeof progressRaw?.computed_progress_percent === "number"
            ? Math.round(progressRaw.computed_progress_percent)
            : undefined;
        const pctCalc =
          total > 0 ? Math.round((done / total) * 100) : pctFromBack ?? 0;

        const ratingAverage = core.review != null ? Number(core.review) : null;
        const ratingCount =
          typeof core.review_count === "number" ? core.review_count : 0;
        const reviewRating =
          typeof progressRaw?.review_rating === "number"
            ? progressRaw.review_rating
            : typeof core.user_review_rating === "number"
            ? core.user_review_rating
            : null;
        const reviewComment = progressRaw?.review_comment ?? core.user_review_comment ?? null;

        const progress: Progress = {
          done,
          total,
          nextAction: progressRaw?.nextAction || (done > 0 ? "Continue a Estudar" : "Começar"),
          enrolledAt: progressRaw?.enrolledAt || progressRaw?.started_at,
          pct: pctFromBack ?? pctCalc,
          status: progressRaw?.status ?? null,
          completed_at: progressRaw?.completed_at ?? null,
          certificate: progressRaw?.certificate ?? null,
          reviewRating,
          reviewComment,
        };

        const nextLessonDate = progress.enrolledAt
          ? new Date(progress.enrolledAt).toLocaleDateString("pt-BR")
          : undefined;

        const vmBuilt = {
          id: core.id,
          title,
          category,
          thumbnail_url: core.thumbnail_url,
          description,
          learn,
          sections: orderedSections,
          instructor: { name: instructorName, initials },
          includes,
          requirements: reqs,
          audience,
          progress,
          nextLessonDate,
          ratingAverage,
          ratingCount,
        };

        if (mounted) setVm(vmBuilt);
      } catch (e: any) {
        if (mounted) setErr(e?.message || "Erro ao carregar a trilha");
      } finally {
        if (mounted) setLoading(false);
      }
    }

    fetchAll();
    return () => {
      mounted = false;
    };
  }, [id]);

  const fetchCertificate = useCallback(async () => {
    if (!vm?.id) return null;
    const trailId = vm.id;
    const { data } = await http.get<{
      certificate_hash: string;
      credential_id: string;
      issued_at?: string | null;
    }>(`/certificates/me/trails/${trailId}`);

    const normalized = {
      hash: data.certificate_hash,
      credential_id: data.credential_id,
      issued_at: data.issued_at ?? null,
    } as CertificateSummary;

    setVm((prev) =>
      prev && prev.id === trailId
        ? {
            ...prev,
            progress: {
              ...prev.progress,
              certificate: normalized,
            },
          }
        : prev
    );

    return normalized;
  }, [vm?.id, setVm]);

  const shareUrl = useMemo(() => {
    if (typeof window === "undefined") return "";
    if (!vm?.id) return window.location.href;
    try {
      return new URL(`/trail-details/${vm.id}`, window.location.origin).toString();
    } catch {
      return window.location.href;
    }
  }, [vm?.id]);

  const canNativeShare = useMemo(() => {
    if (typeof window === "undefined") return false;
    return typeof navigator !== "undefined" && typeof navigator.share === "function";
  }, []);

  useEffect(() => {
    if (!shareOpen) return;
    function handleClickOutside(ev: MouseEvent) {
      if (!shareMenuRef.current) return;
      if (!shareMenuRef.current.contains(ev.target as Node)) {
        setShareOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [shareOpen]);

  useEffect(() => {
    if (copyState === "idle") return;
    const timer = window.setTimeout(() => setCopyState("idle"), 2500);
    return () => window.clearTimeout(timer);
  }, [copyState]);

  useEffect(() => {
    if (!reviewFeedback) return;
    const timer = window.setTimeout(() => setReviewFeedback(null), 3200);
    return () => window.clearTimeout(timer);
  }, [reviewFeedback]);

  const handleNativeShare = useCallback(async () => {
    if (!shareUrl || !canNativeShare || !vm) return;
    try {
      await navigator.share({ title: vm.title, url: shareUrl });
      setShareOpen(false);
    } catch (error) {
      console.warn("Compartilhamento nativo interrompido", error);
    }
  }, [shareUrl, canNativeShare, vm]);

  const handleCopyLink = useCallback(async () => {
    if (!shareUrl) return;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(shareUrl);
      } else {
        const textArea = document.createElement("textarea");
        textArea.value = shareUrl;
        textArea.setAttribute("readonly", "");
        textArea.style.position = "absolute";
        textArea.style.left = "-9999px";
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand("copy");
        document.body.removeChild(textArea);
      }
      setCopyState("copied");
    } catch (error) {
      console.warn("Falha ao copiar link da trilha", error);
      setCopyState("error");
    }
  }, [shareUrl]);

  const handleSubmitReview = useCallback(
    async (rating: number) => {
      const trailId = vm?.id;
      const currentRating = vm?.progress.reviewRating ?? null;
      if (!trailId || reviewSaving) return;
      if (currentRating === rating) {
        setReviewFeedback({ message: "Esta já é sua avaliação atual.", kind: "success" });
        setHoverRating(null);
        return;
      }
      setReviewSaving(true);
      setReviewFeedback(null);
      try {
        const { data } = await http.post<{
          ok: boolean;
          rating: number;
          average?: number | null;
          count?: number | null;
        }>(`/trails/${trailId}/reviews`, { rating });

        const average =
          typeof data.average === "number" ? Number(data.average) : null;
        const count = typeof data.count === "number" ? data.count : undefined;

        setVm((prev) =>
          prev && prev.id === trailId
            ? {
                ...prev,
                ratingAverage: average ?? prev.ratingAverage,
                ratingCount: typeof count === "number" ? count : prev.ratingCount,
                progress: {
                  ...prev.progress,
                  reviewRating: rating,
                },
              }
            : prev
        );
        setHoverRating(null);
        setReviewFeedback({ message: "Obrigado pela sua avaliação!", kind: "success" });
      } catch (error: any) {
        const statusCode = error?.response?.status;
        if (statusCode === 401) {
          navigate("/login");
          return;
        }
        const message =
          statusCode === 403
            ? "Conclua a trilha para poder avaliá-la."
            : "Não foi possível salvar sua avaliação. Tente novamente.";
        setReviewFeedback({ message, kind: "error" });
      } finally {
        setReviewSaving(false);
      }
    },
    [vm?.id, vm?.progress.reviewRating, navigate, reviewSaving]
  );

  useEffect(() => {
    if (!vm) return;
    if (vm.progress.status !== "COMPLETED") return;
    if (vm.progress.certificate) return;
    fetchCertificate().catch((err) => {
      console.warn("Não foi possível carregar o certificado", err);
    });
  }, [vm?.progress.status, vm?.progress.certificate, fetchCertificate]);

  const pct = useMemo(() => vm?.progress?.pct ?? 0, [vm]);
  const firstItemId = useMemo(() => {
    if (!vm) return null;
    for (const section of vm.sections) {
      if (section.items.length > 0) {
        return section.items[0].id;
      }
    }
    return null;
  }, [vm]);

  const primaryActionLabel = useMemo(() => {
    const status = vm?.progress?.status;
    if (!status) return "Matricular-se";
    if (status === "COMPLETED") return "Revisar";
    if (status === "ENROLLED") return "Continuar";
    return vm?.progress?.nextAction ?? "Continuar";
  }, [vm]);

  const handlePrimaryAction = async () => {
    if (!vm) return;
    setEnrollError(null);
    const status = vm.progress.status;

    if (!status) {
      try {
        setEnrolling(true);
        const { data } = await http.post<{
          ok: boolean;
          trail_id: number;
          first_item_id: number | null;
          progress: {
            done: number;
            total: number;
            computed_progress_percent?: number | null;
            nextAction?: string | null;
            enrolledAt?: string | null;
            status?: string | null;
            completed_at?: string | null;
          } | null;
        }>(`/user-trails/${vm.id}/enroll`);

        if (data.progress) {
          const progressData = data.progress;
          const computedPct = typeof progressData.computed_progress_percent === "number"
            ? Math.round(progressData.computed_progress_percent)
            : vm.progress.pct;

          setVm((prev) =>
            prev
              ? {
                  ...prev,
                  progress: {
                    ...prev.progress,
                    done: progressData.done ?? prev.progress.done,
                    total: progressData.total ?? prev.progress.total,
                    nextAction: progressData.nextAction ?? prev.progress.nextAction,
                    enrolledAt: progressData.enrolledAt ?? prev.progress.enrolledAt,
                    status: progressData.status ?? prev.progress.status,
                    completed_at: progressData.completed_at ?? prev.progress.completed_at,
                    pct: computedPct ?? prev.progress.pct,
                  },
                }
              : prev
          );
        }

        const targetItem = data.first_item_id ?? firstItemId;
        if (targetItem) {
          navigate(`/trilha/${vm.id}/aula/${targetItem}`);
        }
      } catch (error: any) {
        const statusCode = error?.response?.status;
        if (statusCode === 401) {
          navigate("/login");
        } else {
          setEnrollError("Não foi possível realizar a matrícula. Tente novamente.");
        }
      } finally {
        setEnrolling(false);
      }
      return;
    }

    if (firstItemId) {
      navigate(`/trilha/${vm.id}/aula/${firstItemId}`);
    }
  };

  const handleViewCertificate = async () => {
    if (!vm) return;
    setCertError(null);

    const existing = vm.progress.certificate;
    if (existing?.hash) {
      navigate(`/certificados/?cert_hash=${existing.hash}`);
      return;
    }

    try {
      setCertLoading(true);
      const cert = await fetchCertificate();
      if (!cert?.hash) {
        setCertError("Certificado ainda não disponível. Tente novamente em instantes.");
        return;
      }
      navigate(`/certificados/?cert_hash=${cert.hash}`);
    } catch (err) {
      setCertError("Não foi possível abrir o certificado agora.");
    } finally {
      setCertLoading(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <section className="trail"><div className="trail__container"><div className="skeleton">Carregando trilha…</div></div></section>
      </Layout>
    );
  }

  if (err || !vm) {
    return (
      <Layout>
        <section className="trail">
          <div className="trail__container">
            <div className="error">
              {err ?? "Não foi possível carregar a trilha."}
            </div>
          </div>
        </section>
      </Layout>
    );
  }

  return (
    <Layout>
      <section className="trail">
        <div className="trail__container">
          <header className="trail-header">
            <div>
              <h1 className="trail-title">{vm.title}</h1>
              <div className="trail-meta">
                <span className="trail-meta__label">Categoria: </span>
                <span className="trail-meta__value">{vm.category}</span>
              </div>
            </div>
            <div className="trail-actions">
              <div className="share-group" ref={shareMenuRef}>
                <button
                  className="btn btn-ghost"
                  type="button"
                  onClick={() => setShareOpen((prev) => !prev)}
                  aria-haspopup="menu"
                  aria-expanded={shareOpen}
                >
                  Compartilhar
                </button>
                {shareOpen && (
                  <div className="share-menu" role="menu">
                    {canNativeShare && (
                      <button type="button" className="share-menu__item" onClick={handleNativeShare}>
                        Enviar pelo dispositivo…
                      </button>
                    )}
                    <button type="button" className="share-menu__item" onClick={handleCopyLink}>
                      {copyState === "copied" ? "Link copiado!" : "Copiar link"}
                    </button>
                    {copyState === "error" && (
                      <div className="share-menu__feedback" role="status">
                        Não foi possível copiar automaticamente. Use Ctrl+C.
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </header>

          <div className="trail-grid">
            <main className="trail-main">
              <div className="trail-cover">
                <img src={vm.thumbnail_url} alt={vm.title} />
              </div>

              {vm.description && (
                <section className="trail-about card">
                  <h2 className="section-title">Sobre o curso</h2>
                  <p className="section-text">{vm.description}</p>
                </section>
              )}

              {vm.learn?.length > 0 && (
                <section className="trail-learn card">
                  <h3 className="section-title">O que você aprenderá?</h3>
                  <ul className="bullets">
                    {vm.learn.map((li, i) => (
                      <li key={i}>{li}</li>
                    ))}
                  </ul>
                </section>
              )}

              <section className="trail-content card">
                <h3 className="section-title">Conteúdo do curso</h3>
                <div className="accordion">
                  {vm.sections.map((sec, idx) => (
                    <details key={sec.id} className="accordion__item" open={idx === 0}>
                      <summary className="accordion__summary">
                        <span>{sec.title}</span>
                        <span className="accordion__chev">▾</span>
                      </summary>
                      <div className="accordion__panel">
                        {sec.items.length === 0 ? (
                          <div className="empty">Sem aulas adicionadas ainda.</div>
                        ) : (
                          <ul className="content-list">
                            {sec.items.map((it) => (
                              <li key={it.id} className="content-list__item">
                                <span className="content-list__icon">●</span>
                                <span className="content-list__title">{it.title}</span>
                                {secondsToMMSS(it.duration_seconds) && (
                                  <span className="content-list__duration">{secondsToMMSS(it.duration_seconds)}</span>
                                )}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </details>
                  ))}
                </div>
              </section>

              <section className="trail-cert card">
                <div className="cert-grid">
                  <div>
                    <h3 className="section-title">Receba um certificado</h3>
                    <p>Adicione este certificado ao seu currículo para demonstrar suas habilidades!</p>
                  </div>
                  <div className="cert-img">
                    <img
                      src="https://preview.tutorlms.com/certificate-templates/default/preview.png"
                      alt="Modelo de certificado"
                    />
                  </div>
                </div>
              </section>
            </main>

            <aside className="trail-aside">
              <div className="card trail-progress">
                <div className="progress-row">
                  <div className="progress-text">
                    <div className="progress-count">
                      {vm.progress.done}/{vm.progress.total}
                    </div>
                    <div className="progress-label">{pct}% Completo</div>
                  </div>
                  <div className="progress-bar">
                    <span style={{ width: `${pct}%` }} />
                  </div>
                </div>
                {vm.progress.status && (
                  <div className={`progress-status status-${vm.progress.status.toLowerCase()}`}>
                    {formatStatusLabel(vm.progress.status)}
                  </div>
                )}
                {vm.progress.completed_at && (
                  <div className="progress-meta">
                    Concluída em {new Date(vm.progress.completed_at).toLocaleDateString("pt-BR")}
                  </div>
                )}
                <button
                  type="button"
                  className="btn btn-primary btn-block"
                  onClick={handlePrimaryAction}
                  disabled={enrolling || (!firstItemId && vm.progress.status !== "ENROLLED")}
                >
                  {enrolling ? "Processando…" : primaryActionLabel}
                </button>
                {vm.progress.status === "COMPLETED" ? (
                  <button
                    type="button"
                    className="btn btn-secondary btn-block cert-button"
                    onClick={handleViewCertificate}
                    disabled={certLoading}
                  >
                    {certLoading ? "Abrindo certificado…" : "Ver certificado"}
                  </button>
                ) : null}
                {vm.progress.certificate?.issued_at && (
                  <div className="cert-issued">
                    Certificado emitido em {new Date(vm.progress.certificate.issued_at).toLocaleDateString("pt-BR")}
                  </div>
                )}
                {certError && (
                  <div className="cert-error" role="alert">
                    {certError}
                  </div>
                )}
                {enrollError && (
                  <div className="enroll-error" role="alert">
                    {enrollError}
                  </div>
                )}
                <ul className="mini-list">
                  <li>Conclua todas as lições para marcar este curso como concluído</li>
                  {vm.nextLessonDate && (
                    <li>
                      Você se matriculou no curso em <strong>{vm.nextLessonDate}</strong>
                    </li>
                  )}
                </ul>
                <div className="divider" />
                <div className="mini-list__item">🏅 Certificado de conclusão</div>
              </div>

            <div className="card review-card">
              <h4 className="card-title">Avaliações</h4>
              <div className="review-summary">
                <div className="review-summary__value">
                  {vm.ratingAverage != null ? vm.ratingAverage.toFixed(1) : "—"}
                </div>
                <div className="review-summary__meta">
                  <div
                    className="review-summary__stars"
                    aria-label={
                      vm.ratingAverage != null
                        ? `Avaliação média ${vm.ratingAverage.toFixed(1)} de 5`
                        : "Sem avaliações registradas"
                    }
                  >
                    {[1, 2, 3, 4, 5].map((value) => {
                      const filled = vm.ratingAverage != null && vm.ratingAverage >= value - 0.25;
                      return (
                        <span
                          key={`avg-${value}`}
                          className={`review-star-icon${filled ? " is-filled" : ""}`}
                          aria-hidden="true"
                        >
                          ★
                        </span>
                      );
                    })}
                  </div>
                  <div className="review-summary__count">
                    {vm.ratingCount > 0
                      ? `${vm.ratingCount} ${vm.ratingCount === 1 ? "avaliação" : "avaliações"}`
                      : "Seja o primeiro a avaliar"}
                  </div>
                </div>
              </div>
              {vm.progress.status === "COMPLETED" ? (
                <div className="review-actions">
                  <p className="review-actions__label">
                    {vm.progress.reviewRating
                      ? "Sua avaliação"
                      : "Avalie esta trilha"}
                  </p>
                  <div
                    className="review-stars"
                    role="radiogroup"
                    aria-label="Defina sua avaliação para esta trilha"
                  >
                    {[1, 2, 3, 4, 5].map((value) => {
                      const activeBase = vm.progress.reviewRating || 0;
                      const isActive =
                        (hoverRating ?? activeBase) >= value;
                      return (
                        <button
                          key={`user-${value}`}
                          type="button"
                          className={`review-star${isActive ? " is-active" : ""}`}
                          onMouseEnter={() => setHoverRating(value)}
                          onMouseLeave={() => setHoverRating(null)}
                          onFocus={() => setHoverRating(value)}
                          onBlur={() => setHoverRating(null)}
                          onClick={() => handleSubmitReview(value)}
                          role="radio"
                          aria-checked={vm.progress.reviewRating === value}
                          aria-label={`${value} ${value === 1 ? "estrela" : "estrelas"}`}
                          disabled={reviewSaving}
                        >
                          ★
                        </button>
                      );
                    })}
                  </div>
                  <span className="review-hint">
                    {reviewSaving
                      ? "Salvando sua avaliação…"
                      : vm.progress.reviewRating
                      ? "Clique nas estrelas para ajustar sua nota."
                      : "Compartilhe sua opinião após concluir a trilha."}
                  </span>
                  {reviewFeedback && (
                    <div
                      className={`review-feedback review-feedback--${reviewFeedback.kind}`}
                      role="status"
                    >
                      {reviewFeedback.message}
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            <div className="card instructor">
              <h4 className="card-title">Um curso de</h4>
              <div className="instructor-row">
                <div className="avatar">{vm.instructor.initials}</div>
                <div className="instructor-name">{vm.instructor.name}</div>
                </div>
              </div>

              {vm.includes?.length > 0 && (
                <div className="card">
                  <h4 className="card-title">Materiais inclusos</h4>
                  <ul className="tick-list">
                    {vm.includes.map((s, i) => (
                      <li key={`${s}-${i}`}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {vm.requirements?.length > 0 && (
                <div className="card">
                  <h4 className="card-title">Requisitos</h4>
                  <ul className="dot-list">
                    {vm.requirements.map((s, i) => (
                      <li key={`${s}-${i}`}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {vm.audience?.length > 0 && (
                <div className="card">
                  <h4 className="card-title">Público</h4>
                  <ul className="dot-list">
                    {vm.audience.map((s, i) => (
                      <li key={`${s}-${i}`}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}
            </aside>
          </div>
        </div>
      </section>
    </Layout>
  );
}
