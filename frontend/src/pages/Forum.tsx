import { useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { Link, Route, Routes, useNavigate, useParams } from "react-router-dom";
import Layout from "../components/Layout";
import Avatar from "../components/Avatar";
import { http } from "../lib/http";
import type { PaginationMeta } from "../types/Pagination";
import { useAuth } from "../hooks/useAuth";
import "../styles/Forum.css";

// ---- Types ---------------------------------------------------------------

type ForumAuthor = {
  user_id: number;
  username: string;
  profile_pic_url: string | null;
};

type ForumSummary = {
  id: number;
  slug: string;
  title: string;
  description?: string | null;
  is_general: boolean;
  trail_id?: number | null;
  trail_name?: string | null;
  topics_count: number;
  posts_count: number;
  last_activity_at?: string | null;
};

type TopicSummary = {
  id: number;
  forum_id: number;
  title: string;
  created_at: string;
  updated_at: string;
  author?: ForumAuthor | null;
  posts_count: number;
  last_post_at?: string | null;
};

type TopicDetail = {
  id: number;
  forum: ForumSummary;
  title: string;
  created_at: string;
  updated_at: string;
  author?: ForumAuthor | null;
  posts_count: number;
  last_post_at?: string | null;
};

type ForumPost = {
  id: number;
  topic_id: number;
  content: string;
  created_at: string;
  updated_at: string;
  author?: ForumAuthor | null;
  parent_post_id?: number | null;
  replies?: ForumPost[];
};

type ForumListPayload = {
  forums?: ForumSummary[];
};

type ForumTopicsPayload = {
  forum: ForumSummary;
  topics: TopicSummary[];
  pagination?: PaginationMeta | null;
};

type TopicPostsPayload = {
  topic: TopicDetail;
  posts: ForumPost[];
  pagination?: PaginationMeta | null;
};

type CreateTopicResponse = {
  topic?: TopicSummary;
  forum?: ForumSummary;
};

type CreatePostResponse = {
  post?: ForumPost;
  topic?: TopicDetail;
  forum?: ForumSummary;
};

// ---- Helpers ------------------------------------------------------------

const TOPICS_PAGE_SIZE = 10;
const POSTS_PAGE_SIZE = 20;

function formatDateTime(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function formatRelativeTime(value?: string | null): string {
  if (!value) return "Sem atividade recente";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Sem atividade recente";
  const diffMs = date.getTime() - Date.now();
  const absMs = Math.abs(diffMs);
  const rtf = new Intl.RelativeTimeFormat("pt-BR", { numeric: "auto" });

  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;
  const month = 30 * day;

  if (absMs < hour) {
    const minutes = Math.round(diffMs / minute);
    return rtf.format(minutes, "minute");
  }
  if (absMs < day) {
    const hours = Math.round(diffMs / hour);
    return rtf.format(hours, "hour");
  }
  if (absMs < month) {
    const days = Math.round(diffMs / day);
    return rtf.format(days, "day");
  }
  return formatDateTime(value);
}

function emptyStateMessage(show: boolean, message: string) {
  if (!show) return null;
  return (
    <div className="forum-empty" role="status">
      {message}
    </div>
  );
}

// ---- Forum list view ----------------------------------------------------

function ForumListView() {
  const [forums, setForums] = useState<ForumSummary[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await http.get<ForumListPayload>("/forums/");
        if (cancelled) return;
        setForums(response.data.forums ?? []);
      } catch (err: any) {
        if (cancelled) return;
        const detail = err?.response?.data?.detail ?? "Não foi possível carregar os fóruns.";
        setError(detail);
      } finally {
        if (cancelled) return;
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return forums;
    return forums.filter((forum) => {
      const inTitle = forum.title.toLowerCase().includes(term);
      const inDesc = (forum.description ?? "").toLowerCase().includes(term);
      const inTrail = (forum.trail_name ?? "").toLowerCase().includes(term);
      return inTitle || inDesc || inTrail;
    });
  }, [forums, search]);

  return (
    <div className="forum-page">
      <header className="forum-header">
        <div>
          <h1 className="forum-title">Fóruns</h1>
          <p className="forum-subtitle">
            Encontre a comunidade certa para compartilhar dúvidas e aprendizados.
          </p>
        </div>
        <div className="forum-search">
          <label htmlFor="forum-search-input" className="sr-only">
            Pesquisar fóruns
          </label>
          <input
            id="forum-search-input"
            type="search"
            placeholder="Pesquisar fóruns..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
      </header>

      {loading && <div className="forum-loading">Carregando fóruns…</div>}
      {error && !loading && (
        <div className="forum-error" role="alert">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="forum-card-grid">
          {filtered.map((forum) => (
            <Link
              key={forum.id}
              to={`${forum.id}`}
              className={`forum-card ${forum.is_general ? "is-general" : ""}`}
            >
              <div className="forum-card-header">
                <h2>{forum.title}</h2>
                {forum.is_general && <span className="forum-badge">Geral</span>}
              </div>
              <p className="forum-card-description">
                {forum.description || "Discussões abertas para a comunidade."}
              </p>
              <dl className="forum-card-meta">
                <div>
                  <dt>Tópicos</dt>
                  <dd>{forum.topics_count}</dd>
                </div>
                <div>
                  <dt>Postagens</dt>
                  <dd>{forum.posts_count}</dd>
                </div>
                <div>
                  <dt>Última atividade</dt>
                  <dd>{formatRelativeTime(forum.last_activity_at)}</dd>
                </div>
              </dl>
              {forum.trail_name && (
                <div className="forum-card-footer">Relacionado à trilha {forum.trail_name}</div>
              )}
            </Link>
          ))}
        </div>
      )}

      {emptyStateMessage(!loading && !error && filtered.length === 0, "Nenhum fórum encontrado.")}
    </div>
  );
}

// ---- Topics view --------------------------------------------------------

function ForumTopicsView() {
  const params = useParams();
  const forumId = params.forumId ?? "";
  const [forum, setForum] = useState<ForumSummary | null>(null);
  const [topics, setTopics] = useState<TopicSummary[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showComposer, setShowComposer] = useState(false);
  const [draftTitle, setDraftTitle] = useState("");
  const [draftContent, setDraftContent] = useState("");
  const [composerError, setComposerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const isAuthenticated = Boolean(user);

  useEffect(() => {
    setPage(1);
    setSearch("");
  }, [forumId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await http.get<ForumTopicsPayload>(`/forums/${forumId}/topics`, {
          params: { page, page_size: TOPICS_PAGE_SIZE },
        });
        if (cancelled) return;
        setForum(response.data.forum);
        setTopics(response.data.topics ?? []);
        setPagination(response.data.pagination ?? null);
      } catch (err: any) {
        if (cancelled) return;
        const detail = err?.response?.data?.detail ?? "Não foi possível carregar os tópicos.";
        setError(detail);
        setForum(null);
        setTopics([]);
        setPagination(null);
      } finally {
        if (cancelled) return;
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [forumId, page]);

  const filteredTopics = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return topics;
    return topics.filter((topic) => {
      const inTitle = topic.title.toLowerCase().includes(term);
      const inAuthor = (topic.author?.username ?? "").toLowerCase().includes(term);
      return inTitle || inAuthor;
    });
  }, [topics, search]);

  const totalPages = useMemo(() => Math.max(1, pagination?.pages ?? 1), [pagination?.pages]);

  function goToPage(next: number) {
    const bounded = Math.min(Math.max(1, next), totalPages);
    setPage(bounded);
  }

  async function handleCreateTopic(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draftTitle.trim() || !draftContent.trim()) {
      setComposerError("Preencha o título e a mensagem.");
      return;
    }
    try {
      setSubmitting(true);
      setComposerError(null);
      const payload = {
        title: draftTitle.trim(),
        content: draftContent.trim(),
      };
      const response = await http.post<CreateTopicResponse>(`/forums/${forumId}/topics`, payload);
      const createdTopic = response.data.topic;
      const updatedForum = response.data.forum;
      if (updatedForum) setForum(updatedForum);
      setDraftTitle("");
      setDraftContent("");
      setShowComposer(false);
      if (createdTopic?.id) {
        navigate(`/foruns/${forumId}/topicos/${createdTopic.id}`);
      } else {
        // fallback: recarrega tópicos
        setPage(1);
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? "Não foi possível criar o tópico.";
      setComposerError(detail);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="forum-page">
      <header className="forum-header">
        <div>
          <p className="forum-breadcrumb">
            <Link to="/foruns">← Voltar para os fóruns</Link>
          </p>
          <h1 className="forum-title">{forum?.title ?? "Fórum"}</h1>
          {!!forum?.description && <p className="forum-subtitle">{forum.description}</p>}
        </div>
        <div className="forum-search">
          <label htmlFor="topic-search-input" className="sr-only">
            Pesquisar tópicos
          </label>
          <input
            id="topic-search-input"
            type="search"
            placeholder="Pesquisar tópicos..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
      </header>

      <div className="forum-actions">
        {(!authLoading && !isAuthenticated) && (
          <div className="forum-login-hint">
            <span>Quer iniciar uma discussão?</span>
            <Link to="/login">Entre na sua conta</Link>
          </div>
        )}
        {isAuthenticated && (
          <button
            type="button"
            className="forum-primary-btn"
            onClick={() => setShowComposer((value) => !value)}
          >
            {showComposer ? "Cancelar" : "Criar tópico"}
          </button>
        )}
      </div>

      {showComposer && isAuthenticated && (
        <form className="forum-composer" onSubmit={handleCreateTopic}>
          <div className="form-group">
            <label htmlFor="new-topic-title">Título</label>
            <input
              id="new-topic-title"
              type="text"
              value={draftTitle}
              onChange={(event) => setDraftTitle(event.target.value)}
              placeholder="Sobre o que você quer conversar?"
              maxLength={160}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="new-topic-content">Mensagem</label>
            <textarea
              id="new-topic-content"
              value={draftContent}
              onChange={(event) => setDraftContent(event.target.value)}
              placeholder="Compartilhe detalhes, contexto ou dúvidas para a comunidade."
              rows={6}
              required
            />
          </div>
          {composerError && (
            <div className="forum-error" role="alert">
              {composerError}
            </div>
          )}
          <button type="submit" className="forum-primary-btn" disabled={submitting}>
            {submitting ? "Publicando…" : "Publicar tópico"}
          </button>
        </form>
      )}

      {loading && <div className="forum-loading">Carregando tópicos…</div>}
      {error && !loading && (
        <div className="forum-error" role="alert">
          {error}
        </div>
      )}

      {!loading && !error && (
        <ul className="forum-topic-list">
          {filteredTopics.map((topic) => (
            <li key={topic.id} className="forum-topic-card">
              <Link to={`topicos/${topic.id}`}>
                <h2>{topic.title}</h2>
                <div className="forum-topic-meta">
                  <span>
                    {topic.posts_count === 1
                      ? "1 resposta"
                      : `${topic.posts_count} respostas`}
                  </span>
                  <span>{topic.author ? `Criado por ${topic.author.username}` : "Autor desconhecido"}</span>
                  <span>Última atividade {formatRelativeTime(topic.last_post_at)}</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {emptyStateMessage(!loading && !error && filteredTopics.length === 0, "Nenhum tópico encontrado.")}

      {pagination && pagination.pages > 1 && (
        <div className="forum-pagination">
          <button type="button" onClick={() => goToPage(page - 1)} disabled={page <= 1}>
            Anterior
          </button>
          <span>
            Página {page} de {totalPages}
          </span>
          <button type="button" onClick={() => goToPage(page + 1)} disabled={page >= totalPages}>
            Próxima
          </button>
        </div>
      )}
    </div>
  );
}

// ---- Topic posts view ---------------------------------------------------

function TopicPostsView() {
  const params = useParams();
  const topicId = params.topicId ?? "";
  const [data, setData] = useState<TopicPostsPayload | null>(null);
  const [pagination, setPagination] = useState<PaginationMeta | null>(null);
  const [page, setPage] = useState(1);
  const [refreshKey, setRefreshKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [replyContent, setReplyContent] = useState("");
  const [replyError, setReplyError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [replyingTo, setReplyingTo] = useState<ForumPost | null>(null);
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const isAuthenticated = Boolean(user);

  useEffect(() => {
    setPage(1);
  }, [topicId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await http.get<TopicPostsPayload>(`/forums/topics/${topicId}/posts`, {
          params: { page, page_size: POSTS_PAGE_SIZE },
        });
        if (cancelled) return;
        setData(response.data);
        setPagination(response.data.pagination ?? null);
      } catch (err: any) {
        if (cancelled) return;
        const detail = err?.response?.data?.detail ?? "Não foi possível carregar o tópico.";
        setError(detail);
        setData(null);
        setPagination(null);
      } finally {
        if (cancelled) return;
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [topicId, page, refreshKey]);

  const totalPages = useMemo(() => Math.max(1, pagination?.pages ?? 1), [pagination?.pages]);

  function goToPage(next: number) {
    const bounded = Math.min(Math.max(1, next), totalPages);
    setPage(bounded);
  }

  async function handleReply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!replyContent.trim()) {
      setReplyError("Escreva uma mensagem para responder.");
      return;
    }
    try {
      setSubmitting(true);
      setReplyError(null);
      const payload = {
        content: replyContent.trim(),
        parent_post_id: replyingTo?.id ?? null,
      };
      const response = await http.post<CreatePostResponse>(`/forums/topics/${topicId}/posts`, payload);
      const createdPost = response.data.post;
      const updatedTopic = response.data.topic;
      if (updatedTopic) {
        setData((current) => (current ? { ...current, topic: updatedTopic } : current));
      }

      const fallbackTotal =
        data?.topic?.posts_count ??
        pagination?.total ??
        (data?.posts?.length ?? 0);
      const totalPosts = updatedTopic?.posts_count ?? (createdPost ? fallbackTotal + 1 : fallbackTotal);
      const lastPage = Math.max(1, Math.ceil(totalPosts / POSTS_PAGE_SIZE));

      if (lastPage !== page) {
        setPage(lastPage);
      } else {
        setRefreshKey((value) => value + 1);
      }

      setReplyContent("");
      setReplyingTo(null);
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? "Não foi possível publicar a resposta.";
      setReplyError(detail);
    } finally {
      setSubmitting(false);
    }
  }

  const topic = data?.topic;
  const posts = data?.posts ?? [];

  function startReply(post: ForumPost) {
    setReplyingTo(post);
    setReplyContent("");
    window.requestAnimationFrame(() => {
      document.getElementById("reply-content")?.focus({ preventScroll: false });
    });
  }

  function renderPosts(tree: ForumPost[], depth = 0): ReactNode {
    if (!tree.length) return null;
    const listClass = depth === 0 ? "forum-post-list" : "forum-post-list forum-post-replies";
    return (
      <ul className={listClass}>
        {tree.map((post) => {
          const isTarget = replyingTo?.id === post.id;
          return (
            <li key={post.id} className={`forum-post ${isTarget ? "is-target" : ""}`}>
              <header>
                <div className="forum-post-author">
                  <Avatar
                    name={post.author?.username ?? "Participante"}
                    src={post.author?.profile_pic_url ?? null}
                    size={40}
                  />
                  <div className="forum-post-author-meta">
                    <strong>{post.author?.username ?? "Participante"}</strong>
                    <time dateTime={post.created_at}>{formatDateTime(post.created_at)}</time>
                  </div>
                </div>
              </header>
              <p>{post.content}</p>
              {isAuthenticated && (
                <div className="forum-post-actions">
                  <button
                    type="button"
                    className="forum-reply-link"
                    onClick={() => startReply(post)}
                  >
                    Responder
                  </button>
                </div>
              )}
              {renderPosts(post.replies ?? [], depth + 1)}
            </li>
          );
        })}
      </ul>
    );
  }

  return (
    <div className="forum-page">
      <header className="forum-header">
        <div>
          <p className="forum-breadcrumb">
            <Link to="/foruns">← Fóruns</Link>
            {topic?.forum?.id && (
              <>
                <span className="divider">/</span>
                <Link to={`/foruns/${topic.forum.id}`}>{topic.forum.title}</Link>
              </>
            )}
          </p>
          <h1 className="forum-title">{topic?.title ?? "Tópico"}</h1>
          {topic?.author && (
            <p className="forum-subtitle">
              Criado por {topic.author.username} em {formatDateTime(topic.created_at)}
            </p>
          )}
        </div>
        <button type="button" className="forum-secondary-btn" onClick={() => navigate(-1)}>
          Voltar
        </button>
      </header>

      {loading && <div className="forum-loading">Carregando postagens…</div>}
      {error && !loading && (
        <div className="forum-error" role="alert">
          {error}
        </div>
      )}

      {!loading && !error && renderPosts(posts)}

      {emptyStateMessage(!loading && !error && posts.length === 0, "Nenhuma mensagem publicada ainda.")}

      {pagination && pagination.pages > 1 && (
        <div className="forum-pagination">
          <button type="button" onClick={() => goToPage(page - 1)} disabled={page <= 1}>
            Anterior
          </button>
          <span>
            Página {page} de {totalPages}
          </span>
          <button type="button" onClick={() => goToPage(page + 1)} disabled={page >= totalPages}>
            Próxima
          </button>
        </div>
      )}

      {(!authLoading && !isAuthenticated) && (
        <div className="forum-login-hint">
          <span>Quer participar?</span>
          <Link to="/login">Entre para responder</Link>
        </div>
      )}

      {isAuthenticated && (
        <form className="forum-reply" onSubmit={handleReply}>
          <label htmlFor="reply-content">Responder</label>
          {replyingTo && (
            <div className="forum-replying-to" role="status">
              Respondendo a <strong>{replyingTo.author?.username ?? "Participante"}</strong>
              <button type="button" onClick={() => setReplyingTo(null)}>
                cancelar
              </button>
            </div>
          )}
          <textarea
            id="reply-content"
            rows={5}
            value={replyContent}
            onChange={(event) => setReplyContent(event.target.value)}
            placeholder="Compartilhe sua contribuição para a discussão"
            required
          />
          {replyError && (
            <div className="forum-error" role="alert">
              {replyError}
            </div>
          )}
          <button type="submit" className="forum-primary-btn" disabled={submitting}>
            {submitting ? "Enviando…" : "Publicar resposta"}
          </button>
        </form>
      )}
    </div>
  );
}

// ---- Fallback -----------------------------------------------------------

function ForumNotFound() {
  return (
    <div className="forum-page">
      <div className="forum-error" role="alert">
        A página de fórum que você tentou acessar não existe.
      </div>
      <Link to="/foruns" className="forum-secondary-btn" style={{ width: "fit-content", marginTop: "1.5rem" }}>
        Voltar aos fóruns
      </Link>
    </div>
  );
}

// ---- Page entry ---------------------------------------------------------

export default function Forum() {
  return (
    <Layout>
      <div className="forum-container">
        <Routes>
          <Route index element={<ForumListView />} />
          <Route path=":forumId" element={<ForumTopicsView />} />
          <Route path=":forumId/topicos/:topicId" element={<TopicPostsView />} />
          <Route path="*" element={<ForumNotFound />} />
        </Routes>
      </div>
    </Layout>
  );
}
