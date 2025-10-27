import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Menu as MenuIcon, X } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { http } from "../lib/http";
import "../styles/Trail.css";
import Layout from "../components/Layout";
import { useAuth } from "../hooks/AuthContext";

const PROGRESS_SAVE_INTERVAL_MS = 15000; // 15s

/** ===== Tipos vindos do seu back ===== */
type Item = {
  id: number;
  title: string;
  duration_seconds?: number | null;
  order_index?: number | null;
  type?: string | null; // "VIDEO" | "QUIZ" | "PDF" etc.
  requires_completion?: boolean | null;
};

type Section = {
  id: number;
  title: string;
  order_index?: number | null;
  items: Item[];
};

type ProgressTotal = {
  done: number;
  total: number;
  computed_progress_percent?: number | null;
  nextAction?: string | null;
  enrolledAt?: string | null;
  status?: string | null;
  completed_at?: string | null;
};

type ItemType = "VIDEO" | "DOC" | "FORM";
type ResourceKind = "PDF" | "IMAGE" | "OTHER";

type FormOption = {
  id: number;
  text: string;
  order_index: number;
};

type FormQuestion = {
  id: number;
  prompt: string;
  type: "ESSAY" | "TRUE_OR_FALSE" | "SINGLE_CHOICE" | "UNKNOWN";
  required: boolean;
  order_index: number;
  points: number;
  options: FormOption[];
};

type FormSchema = {
  id: number;
  title?: string | null;
  description?: string | null;
  min_score_to_pass: number;
  randomize_questions?: boolean | null;
  questions: FormQuestion[];
};

/** ===== Detalhe de item (novo GET no back) ===== */
type ItemDetail = {
  id: number;
  trail_id: number;
  section_id: number | null;
  title: string;
  type: ItemType;
  youtubeId?: string;
  duration_seconds?: number | null;
  required_percentage?: number | null;
  description_html: string;
  prev_item_id?: number | null;
  next_item_id?: number | null;
  form?: FormSchema | null;
  requires_completion?: boolean | null;
  resource_url?: string | null;
  resource_kind?: ResourceKind | null;
};

type FormResult = {
  submission_id: number;
  score: number;
  score_points: number;
  max_points: number;
  max_score: number;
  passed: boolean | null;
  requires_manual_review: boolean;
  answers: {
    question_id: number;
    is_correct: boolean | null;
    points_awarded: number | null;
  }[];
};

type ItemProgress = {
  item_id: number;
  status?: string | null;
  progress_value?: number | null;
  completed_at?: string | null;
};

type SectionProgress = {
  section_id: number;
  title: string;
  total: number;
  done: number;
  percent: number;
};

function YouTubePlayer({
  videoId,
  startAt = 0,
  onProgress,
  onReady,
  maxAllowedPosition,
  seekBlockedLabel,
  playedSeconds = 0,
}: {
  videoId: string;
  startAt?: number;
  onProgress?: (t: { current: number; duration: number }) => void;
  onReady?: (t: { current: number; duration: number }) => void;
  maxAllowedPosition?: number;
  seekBlockedLabel?: string;
  playedSeconds?: number;
}) {
  const surfaceRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const playerRef = useRef<any>(null);
  const timerRef = useRef<number | null>(null);
  const seekWarnTimerRef = useRef<number | null>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [current, setCurrent] = useState(0);
  const [duration, setDuration] = useState(0);
  const [hover, setHover] = useState(false);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(100);
  const [seekWarning, setSeekWarning] = useState(false);

  // velocidade / taxas válidas
  const [speed, setSpeed] = useState(1);
  const [rates, setRates] = useState<number[]>([0.5, 0.75, 1, 1.25, 1.5, 1.75, 2]);

  // fullscreen
  const [isFs, setIsFs] = useState(false);

  const onProgressRef = useRef(onProgress);
  const onReadyRef = useRef(onReady);
  useEffect(() => { onProgressRef.current = onProgress; }, [onProgress]);
  useEffect(() => { onReadyRef.current = onReady; }, [onReady]);

  // carrega API uma vez
  useEffect(() => {
    const w = window as any;
    if (!w.__ytApiPromise) {
      w.__ytApiPromise = new Promise<void>((resolve) => {
        if (!document.getElementById("yt-iframe-api")) {
          const s = document.createElement("script");
          s.id = "yt-iframe-api";
          s.src = "https://www.youtube.com/iframe_api";
          document.body.appendChild(s);
        }
        const prev = w.onYouTubeIframeAPIReady;
        w.onYouTubeIframeAPIReady = () => { prev?.(); resolve(); };
        const tick = () => (w.YT?.Player ? resolve() : setTimeout(tick, 50));
        tick();
      });
    }
  }, []);

  // cria/atualiza player
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const w = (window as any);
      await w.__ytApiPromise;
      if (cancelled || !containerRef.current) return;

      const poll = () => {
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = window.setInterval(() => {
          try {
            const d = playerRef.current?.getDuration?.() ?? 0;
            const c = playerRef.current?.getCurrentTime?.() ?? 0;
            setDuration(d); setCurrent(c);
            if (d > 0) onProgressRef.current?.({ current: c, duration: d });
          } catch {}
        }, 500);
      };

      const start = Math.floor(startAt || 0);

      if (playerRef.current) {
        try {
          playerRef.current.loadVideoById({ videoId, startSeconds: start });
          playerRef.current.pauseVideo();
          setIsPlaying(false);
          poll();
        } catch {}
        return;
      }

      playerRef.current = new w.YT.Player(containerRef.current, {
        videoId,
        host: "https://www.youtube-nocookie.com",
        playerVars: {
            // **visual**
            controls: 0,           // sem barra/controles do YT
            modestbranding: 1,     // reduz marca do YT
            rel: 0,                // relacionados só do mesmo canal
            iv_load_policy: 3,     // sem cards/annotations
            fs: 0,                 // sem botão de fullscreen do YT
            disablekb: 1,          // desativa atalhos do YT
            // **comportamento**
            playsinline: 1,        // evita full no iOS
            // **API/segurança**
            enablejsapi: 1,
            origin: window.location.origin, // importante pra API
            // OBS: showinfo é legacy/ignorado --> remova
            showinfo: 0,          // sem título do vídeo no início
        },
        events: {
          onReady: () => {
            const p = playerRef.current;
            const d = p?.getDuration?.() ?? 0;
            const c = p?.getCurrentTime?.() ?? 0;
            setDuration(d); setCurrent(c);
            setVolume(p?.getVolume?.() ?? 100);
            setMuted(p?.isMuted?.() ?? false);

            // taxas disponíveis
            try {
              const avail = p?.getAvailablePlaybackRates?.() ?? [];
              if (avail.length) {
                setRates(avail as number[]);
                // garante que a velocidade inicial é válida
                const initial = avail.includes(speed) ? speed : 1;
                p.setPlaybackRate?.(initial);
                setSpeed(initial);
              } else {
                p.setPlaybackRate?.(1);
                setSpeed(1);
              }
            } catch {}

            onReadyRef.current?.({ current: c, duration: d });
            poll();
          },
          onStateChange: (e: any) => {
            if (e?.data === 0) {
              // terminou: pausa próximo do fim, mantém progresso máximo
              setIsPlaying(false);
              const safePoint = Math.max(0, (playerRef.current?.getDuration?.() ?? duration) - 0.25);
              try {
                playerRef.current.seekTo(safePoint, true);
                playerRef.current.pauseVideo();
              } catch {}
              setCurrent(playerRef.current?.getDuration?.() ?? duration);
              const finalDuration = playerRef.current?.getDuration?.() ?? duration;
              onProgressRef.current?.({ current: finalDuration, duration: finalDuration });
            } else {
              setIsPlaying(e?.data === 1);
            }
          },
        },
      });
    })();

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [videoId, startAt]);

  // ======== Controles ========
  const togglePlay = () => {
    if (!playerRef.current) return;
    isPlaying ? playerRef.current.pauseVideo() : playerRef.current.playVideo();
  };

  useEffect(() => () => {
    if (seekWarnTimerRef.current) {
      clearTimeout(seekWarnTimerRef.current);
      seekWarnTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!seekBlockedLabel && seekWarnTimerRef.current) {
      clearTimeout(seekWarnTimerRef.current);
      seekWarnTimerRef.current = null;
    }
    if (!seekBlockedLabel) {
      setSeekWarning(false);
    }
  }, [seekBlockedLabel]);

  const handleSeek = (value: number) => {
    if (!playerRef.current) return;
    const t = Math.max(0, Math.min(value, duration || 0));
    let finalTarget = t;
    if (typeof maxAllowedPosition === "number" && Number.isFinite(maxAllowedPosition)) {
      const limit = Math.max(0, Math.min(maxAllowedPosition, duration || maxAllowedPosition));
      if (finalTarget > limit) {
        finalTarget = limit;
        if (seekBlockedLabel) {
          setSeekWarning(true);
          if (seekWarnTimerRef.current) clearTimeout(seekWarnTimerRef.current);
          seekWarnTimerRef.current = window.setTimeout(() => {
            setSeekWarning(false);
            seekWarnTimerRef.current = null;
          }, 2500);
        }
      }
    }
    playerRef.current.seekTo(finalTarget, true);
    setCurrent(finalTarget);
  };

  const toggleMute = () => {
    if (!playerRef.current) return;
    if (muted) { playerRef.current.unMute(); setMuted(false); }
    else { playerRef.current.mute(); setMuted(true); }
  };

  const changeVolume = (v: number) => {
    if (!playerRef.current) return;
    const vv = Math.max(0, Math.min(100, v));
    playerRef.current.setVolume(vv);
    setVolume(vv);
    if (vv === 0 && !muted) setMuted(true);
    if (vv > 0 && muted) setMuted(false);
  };

  const changeSpeed = (val: number) => {
    if (!playerRef.current) return;
    // pega taxa suportada mais próxima
    const sorted = [...rates].sort((a,b)=>Math.abs(a-val)-Math.abs(b-val));
    const target = sorted[0] ?? 1;
    try {
      playerRef.current.setPlaybackRate(target);
      // confirma (alguns vídeos demoram 1 tick pra aplicar)
      setTimeout(() => {
        const applied = playerRef.current?.getPlaybackRate?.();
        if (applied !== target) playerRef.current?.setPlaybackRate?.(target);
      }, 50);
      setSpeed(target);
    } catch {
      setSpeed(1);
      try { playerRef.current.setPlaybackRate(1); } catch {}
    }
  };

  // fullscreen: toggle no wrapper
  useEffect(() => {
    const onFs = () => setIsFs(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", onFs);
    return () => document.removeEventListener("fullscreenchange", onFs);
  }, []);

  const toggleFullscreen = () => {
    const el: any = surfaceRef.current;
    if (!el) return;
    if (!document.fullscreenElement) {
      const req = el.requestFullscreen || el.webkitRequestFullscreen || el.mozRequestFullScreen || el.msRequestFullscreen;
      req?.call(el);
    } else {
      const exit = document.exitFullscreen || (document as any).webkitExitFullscreen || (document as any).mozCancelFullScreen || (document as any).msExitFullscreen;
      exit?.call(document);
    }
  };

  // ======== Helpers ========
  const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`);
  const fmt = (sec: number) => {
    const s = Math.floor(sec % 60);
    const m = Math.floor((sec / 60) % 60);
    const h = Math.floor(sec / 3600);
    if (h > 0) return `${h}:${pad(m)}:${pad(s)}`;
    return `${pad(m)}:${pad(s)}`;
  };
  const playedPct = duration
    ? Math.min(100, (Math.max(current, playedSeconds) / duration) * 100)
    : 0;
  const progressTrack = `linear-gradient(to right, #2563eb ${playedPct}%, rgba(255,255,255,0.2) ${playedPct}%)`;
  const showOverlay = !isPlaying || hover;

  return (
    <div
      className="custom-player"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onMouseMove={() => setHover(true)}
      onContextMenu={(e) => e.preventDefault()}
    >
      <div
        ref={surfaceRef}
        className="ratio-16x9 player-surface"
        onClick={togglePlay}
      >
        <div ref={containerRef} className="ratio-fill iframe-layer" />

        {/* Play central */}
        <button
          className={`cp-center-play ${!isPlaying ? "show" : ""}`}
          onClick={(e) => { e.stopPropagation(); togglePlay(); }}
          aria-label="Reproduzir/Pausar"
        >
          {isPlaying ? "⏸" : "▶"}
        </button>

        {/* Barra inferior */}
        <div className={`cp-bottom ${showOverlay ? "show" : ""}`} onClick={(e) => e.stopPropagation()}>
          {/* play/pause */}
          <button className="cp-btn" onClick={togglePlay} aria-label={isPlaying ? "Pausar" : "Reproduzir"}>
            {isPlaying ? "⏸" : "▶"}
          </button>

          {/* seek */}
          <input
            className="cp-seek"
            type="range"
            min={0}
            max={Math.max(0, Math.floor(duration || 0))}
            value={Math.floor(current || 0)}
            onChange={(e) => handleSeek(Number(e.target.value))}
            style={{
              background: progressTrack
            }}
            aria-label="Progresso"
            title={seekBlockedLabel && typeof maxAllowedPosition === "number" ? seekBlockedLabel : undefined}
          />

          {/* tempo restante */}
          <div className="cp-time">-{fmt(Math.max(0, (duration || 0) - (current || 0)))}</div>

          {/* volume */}
          <button className="cp-icon" onClick={toggleMute} aria-label={muted ? "Desmutar" : "Mutar"}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M4 9h4l5-4v14l-5-4H4V9z" fill="currentColor" opacity={muted ? 0.4 : 1}/>
              {!muted && <path d="M16 8c1.5 1 1.5 7 0 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>}
            </svg>
          </button>
          <input
            className="cp-volume"
            type="range"
            min={0}
            max={100}
            value={volume}
            onChange={(e) => changeVolume(Number(e.target.value))}
            aria-label="Volume"
          />

          {/* velocidade */}
          <select
            className="cp-speed"
            value={speed}
            onChange={(e) => changeSpeed(Number(e.target.value))}
            aria-label="Velocidade"
          >
            {rates.map(v => <option key={v} value={v}>{v}×</option>)}
          </select>

          {/* fullscreen na direita */}
          <button className="cp-btn cp-full" onClick={toggleFullscreen} aria-label={isFs ? "Sair de tela cheia" : "Tela cheia"}>
            {isFs ? "🡽" : "⛶"}
          </button>
          {seekWarning && seekBlockedLabel && (
            <div className="cp-warning" role="status">
              {seekBlockedLabel}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


export default function Trail() {
  const { trailId, itemId } = useParams<{ trailId: string; itemId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [sections, setSections] = useState<Section[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isMobileView, setIsMobileView] = useState(
    () => (typeof window !== "undefined" ? window.innerWidth < 1024 : false)
  );
  const [progress, setProgress] = useState<ProgressTotal | null>(null);
  const [detail, setDetail] = useState<ItemDetail | null>(null);
  const [watch, setWatch] = useState({ current: 0, duration: 0 });
  const [maxWatched, setMaxWatched] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [itemProgress, setItemProgress] = useState<Record<number, ItemProgress>>({});
  const [sectionProgress, setSectionProgress] = useState<Record<number, SectionProgress>>({});
  const sectionsRef = useRef<Section[]>([]);
  const lastProgressSyncRef = useRef<number>(0);
  const prevCanCompleteRef = useRef<boolean>(false);
  const syncProgressInFlightRef = useRef<boolean>(false);
  const isMountedRef = useRef<boolean>(true);
  const resumePositionRef = useRef<number>(0);
  const [formAnswers, setFormAnswers] = useState<Record<number, { selectedOptionId?: number; answerText?: string }>>({});
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formResult, setFormResult] = useState<FormResult | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [lockedItems, setLockedItems] = useState<Record<number, { id: number; title: string } | null>>({});
  const [blockedBy, setBlockedBy] = useState<{ id: number; title: string } | null>(null);
  const [certLoading, setCertLoading] = useState(false);
  const [certError, setCertError] = useState<string | null>(null);

  // quais sections estão abertas (expandidas)
  const [openSections, setOpenSections] = useState<Set<number>>(new Set());

  const isPrivileged = user?.role === "Admin" || user?.role === "Manager";

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    function handleResize() {
      const mobile = window.innerWidth < 1024;
      setIsMobileView(mobile);
      if (!mobile) {
        setSidebarOpen(false);
      }
    }
    if (typeof window !== "undefined") {
      handleResize();
      window.addEventListener("resize", handleResize);
      return () => window.removeEventListener("resize", handleResize);
    }
    return undefined;
  }, []);

  useEffect(() => {
    if (isMobileView) {
      setSidebarCollapsed(false);
    }
  }, [isMobileView]);

  useEffect(() => {
    if (isMobileView) {
      setSidebarOpen(false);
    }
  }, [itemId, isMobileView]);

  useEffect(() => {
    lastProgressSyncRef.current = Date.now();
    prevCanCompleteRef.current = false;
    resumePositionRef.current = 0;
  }, [detail?.id]);

  useEffect(() => {
    if (!isMobileView) return;
    if (sidebarOpen) {
      document.body.classList.add("no-scroll");
    } else {
      document.body.classList.remove("no-scroll");
    }
    return () => {
      document.body.classList.remove("no-scroll");
    };
  }, [sidebarOpen, isMobileView]);

  const loadProgress = useCallback(async () => {
    if (!trailId) return;
    try {
      const [trailRes, itemsRes, sectionsRes] = await Promise.all([
        http.get<ProgressTotal>(`/user-trails/${trailId}/progress`),
        http.get<ItemProgress[]>(`/user-trails/${trailId}/items-progress`),
        http.get<SectionProgress[]>(`/user-trails/${trailId}/sections-progress`),
      ]);

      setProgress(trailRes.data ?? null);

      const itemEntries = (itemsRes.data ?? []).map((ip) => [ip.item_id, ip] as const);
      setItemProgress(Object.fromEntries(itemEntries));

      const sectionEntries = (sectionsRes.data ?? []).map((sp) => [sp.section_id, sp] as const);
      setSectionProgress(Object.fromEntries(sectionEntries));
    } catch (error) {
      const status = (error as any)?.response?.status;
      if (status === 401) {
        const fallbackTotal = sectionsRef.current.reduce((acc, sec) => acc + (sec.items?.length ?? 0), 0);
        setProgress({ done: 0, total: fallbackTotal, computed_progress_percent: 0, nextAction: "Começar" });
        setItemProgress({});
        setSectionProgress({});
        return;
      }
      // eslint-disable-next-line no-console
      console.error("Falha ao carregar progresso da trilha", error);
      setProgress((prev) => prev ?? {
        done: 0,
        total: sectionsRef.current.reduce((acc, sec) => acc + (sec.items?.length ?? 0), 0),
        computed_progress_percent: 0,
        nextAction: "Começar",
      });
    }
  }, [trailId]);

  useEffect(() => {
    if (!sections.length) {
      setLockedItems({});
      return;
    }

    const orderSections = [...sections].sort((a, b) => {
      const aOrd = a.order_index ?? 0;
      const bOrd = b.order_index ?? 0;
      if (aOrd !== bOrd) return aOrd - bOrd;
      return a.id - b.id;
    });

    const next: Record<number, { id: number; title: string } | null> = {};
    let blocker: { id: number; title: string } | null = null;

    const isCompleted = (itemId: number) =>
      itemProgress[itemId]?.status === "COMPLETED";

    for (const section of orderSections) {
      const orderedItems = [...section.items].sort((a, b) => {
        const aOrd = a.order_index ?? 0;
        const bOrd = b.order_index ?? 0;
        if (aOrd !== bOrd) return aOrd - bOrd;
        return a.id - b.id;
      });

      for (const item of orderedItems) {
        const effectiveBlocker =
          blocker && blocker.id === item.id ? null : blocker;
        next[item.id] = effectiveBlocker;

        if (!item.requires_completion) {
          continue;
        }

        const completed = isCompleted(item.id);
        if (blocker && blocker.id === item.id && completed) {
          blocker = null;
        } else if (!blocker && !completed) {
          blocker = {
            id: item.id,
            title: item.title || "Item obrigatório",
          };
        }
      }
    }

    setLockedItems(next);
  }, [sections, itemProgress]);

  // abre a seção da aula atual ao carregar/trocar de item
  useEffect(() => {
    const secWithCurrent = sections.find((s) =>
      s.items.some((i) => String(i.id) === itemId)
    )?.id;
    if (secWithCurrent) {
      setOpenSections((prev) => {
        const next = new Set(prev);
        next.add(secWithCurrent);
        return next;
      });
    }
  }, [sections, itemId]);

  function toggleSection(id: number) {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const handleSidebarToggle = () => {
    if (isMobileView) {
      setSidebarOpen((prev) => !prev);
    } else {
      setSidebarCollapsed((prev) => !prev);
    }
  };

  const handleSidebarClose = () => {
    if (isMobileView) {
      setSidebarOpen(false);
    } else {
      setSidebarCollapsed(true);
    }
  };

  const handleSidebarItemClick = () => {
    if (isMobileView) {
      setSidebarOpen(false);
    }
  };

  function resolveIconClass(type?: string | null) {
    if (type === "QUIZ") return "tutor-icon-quiz-o";
    if (type === "PDF" || type === "DOC") return "tutor-icon-document-text";
    if (type === "FORM") return "tutor-icon-edit";
    return "tutor-icon-brand-youtube-bold";
  }

  const totalDuration = watch.duration || (detail?.duration_seconds ?? 0);

  // % assistido (local; o back guarda progress_value)
  const watchedSeconds = useMemo(() => {
    if (detail?.type !== "VIDEO") return watch.current;
    const candidate = Math.max(maxWatched, watch.current);
    if (!totalDuration) return candidate;
    return Math.min(candidate, totalDuration);
  }, [detail?.type, maxWatched, watch.current, totalDuration]);

  const pct = useMemo(
    () => (totalDuration ? Math.min(100, (watchedSeconds / totalDuration) * 100) : 0),
    [watchedSeconds, totalDuration]
  );

  const canComplete = useMemo(
    () => detail?.type === "VIDEO" && totalDuration > 0 && pct >= (detail.required_percentage ?? 70),
    [detail, pct, totalDuration]
  );

  const seekForwardGrace = 1.5;
  const maxSeekPosition = useMemo(() => {
    if (isPrivileged) return undefined;
    const limit = Math.max(maxWatched + seekForwardGrace, watchedSeconds);
    return totalDuration ? Math.min(limit, totalDuration) : limit;
  }, [isPrivileged, maxWatched, watchedSeconds, totalDuration]);

  const seekBlockedLabel = isPrivileged
    ? undefined
    : "Assista sequencialmente para liberar o restante do vídeo.";

  useEffect(() => {
    if (!detail || detail.type !== "VIDEO") return;
    const progressEntry = itemProgress[detail.id];
    if (!progressEntry) return;
    const stored = progressEntry.progress_value ?? 0;
    if (stored <= 0) return;
    if (resumePositionRef.current === 0) {
      const duration = detail.duration_seconds ?? 0;
      if (duration > 0) {
        const safeUpperBound = Math.max(0, duration - 1);
        resumePositionRef.current = Math.max(0, Math.min(stored, safeUpperBound));
      } else {
        resumePositionRef.current = Math.max(0, stored);
      }
    }
    setMaxWatched((prev) => (stored > prev ? stored : prev));
  }, [detail, itemProgress]);

  const showManualCompletion = detail?.type === "DOC";

  const questionOrderMap = useMemo(() => {
    if (!detail?.form) return new Map<number, number>();
    return new Map(detail.form.questions.map((q, index) => [q.id, index + 1]));
  }, [detail?.form]);

  const blockedTitle = blockedBy?.title?.trim() || "o item obrigatório";
  const blockedTargetId = typeof blockedBy?.id === "number" ? blockedBy.id : null;

  const questionResultMap = useMemo(() => {
    if (!formResult) return new Map<number, FormResult["answers"][number]>();
    return new Map(formResult.answers.map((ans) => [ans.question_id, ans]));
  }, [formResult]);

  const handleOpenCertificate = useCallback(async () => {
    if (!trailId) return;
    setCertError(null);
    try {
      setCertLoading(true);
      const { data } = await http.get<{
        certificate_hash?: string;
      }>(`/certificates/me/trails/${trailId}`);
      const hash = data?.certificate_hash;
      if (hash) {
        navigate(`/certificados/?cert_hash=${hash}`);
        return;
      }
      setCertError("Certificado ainda não disponível. Tente novamente em instantes.");
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      if (typeof detail === "string" && detail.trim()) {
        setCertError(detail);
      } else {
        setCertError("Não foi possível abrir o certificado agora.");
      }
    } finally {
      setCertLoading(false);
    }
  }, [trailId, navigate]);

  const handleOptionChange = (questionId: number, optionId: number) => {
    setFormAnswers((prev) => ({
      ...prev,
      [questionId]: { ...(prev[questionId] ?? {}), selectedOptionId: optionId },
    }));
    setFormError(null);
    setFormResult(null);
  };

  const handleEssayChange = (questionId: number, value: string) => {
    setFormAnswers((prev) => ({
      ...prev,
      [questionId]: { ...(prev[questionId] ?? {}), answerText: value },
    }));
    setFormError(null);
    setFormResult(null);
  };

  const submitFormAnswers = async () => {
    if (!detail || detail.type !== "FORM" || !detail.form) return;

    const missingRequired: number[] = [];
    const answersPayload: { question_id: number; selected_option_id?: number; answer_text?: string }[] = [];

    for (const question of detail.form.questions) {
      const stored = formAnswers[question.id];
      if (question.type === "ESSAY") {
        const text = stored?.answerText?.trim() ?? "";
        if (question.required && !text) {
          missingRequired.push(question.id);
          continue;
        }
        if (text) {
          answersPayload.push({ question_id: question.id, answer_text: text });
        }
      } else {
        const optionId = stored?.selectedOptionId;
        if (question.required && optionId == null) {
          missingRequired.push(question.id);
          continue;
        }
        if (optionId != null) {
          answersPayload.push({
            question_id: question.id,
            selected_option_id: optionId,
          });
        }
      }
    }

    if (missingRequired.length > 0) {
      const labels = missingRequired
        .map((id) => questionOrderMap.get(id) ?? id)
        .join(", ");
      setFormError(`Responda as questões obrigatórias (${labels}).`);
      return;
    }

    setFormError(null);
    setFormSubmitting(true);
    try {
      const response = await http.post<FormResult>(
        `/trails/${trailId}/items/${detail.id}/form-submissions`,
        { answers: answersPayload }
      );
      setFormResult(response.data);
      await loadProgress();
    } catch (error: any) {
      const status = error?.response?.status;
      const data = error?.response?.data;
      if (status === 422) {
        if (Array.isArray(data?.missing_questions) && data.missing_questions.length) {
          const labels = (data.missing_questions as number[])
            .map((id: number) => questionOrderMap.get(id) ?? id)
            .join(", ");
          setFormError(`Responda todas as questões obrigatórias (${labels}).`);
        } else if (Array.isArray(data?.invalid_questions) && data.invalid_questions.length) {
          setFormError("Uma ou mais respostas são inválidas para este formulário.");
        } else if (typeof data?.detail === "string") {
          setFormError(data.detail);
        } else {
          setFormError("Não foi possível validar suas respostas. Verifique e tente novamente.");
        }
      } else {
        setFormError("Não foi possível enviar suas respostas. Tente novamente.");
      }
    } finally {
      setFormSubmitting(false);
    }
  };

  // carrega sidebar + progresso + detalhe atual
  useEffect(() => {
    let mounted = true;
    (async () => {
      if (!trailId || !itemId) return;
      setLoading(true);
      try {
        const [sectionsResult, detailResult] = await Promise.allSettled([
          http.get<Section[]>(`/trails/${trailId}/sections-with-items`),
          http.get<ItemDetail>(`/trails/${trailId}/items/${itemId}`),
        ]);

        if (!mounted) return;

        if (sectionsResult.status === "fulfilled") {
          const secsData = sectionsResult.value.data ?? [];
          sectionsRef.current = secsData;
          setSections(secsData);
        } else {
          throw sectionsResult.reason;
        }

        let resolvedDetail: ItemDetail | null = null;

        if (detailResult.status === "fulfilled") {
          resolvedDetail = detailResult.value.data as ItemDetail;
          setBlockedBy(null);
          setDetail(resolvedDetail);
          setMaxWatched(0);
          if (resolvedDetail.type === "VIDEO") {
            setWatch({
              current: 0,
              duration: resolvedDetail.duration_seconds ?? 0,
            });
          } else {
            setWatch({ current: 0, duration: 0 });
          }
        } else {
          const error: any = detailResult.reason;
          const status = error?.response?.status;
          if (status === 423 && error?.response?.data?.reason === "item_locked") {
            const blocked = error.response?.data?.blocked_item;
            setBlockedBy(
              blocked && typeof blocked.id === "number"
                ? { id: blocked.id, title: blocked.title ?? "" }
                : null
            );
            setDetail(null);
            setMaxWatched(0);
            setWatch({ current: 0, duration: 0 });
          } else if (status === 404) {
            setBlockedBy(null);
            setDetail(null);
            setMaxWatched(0);
            setWatch({ current: 0, duration: 0 });
          } else {
            throw error;
          }
        }

        setFormAnswers({});
        setFormResult(null);
        setFormError(null);
        setCertError(null);

        await loadProgress();
      } catch (error) {
        if (!mounted) return;
        // eslint-disable-next-line no-console
        console.error("Falha ao carregar conteúdo da trilha", error);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [trailId, itemId, loadProgress]);

  // salva progresso periodicamente para reduzir carga no backend
  useEffect(() => {
    if (!detail || detail.type !== "VIDEO") return;

    const previouslyComplete = prevCanCompleteRef.current;
    const becameComplete = canComplete && !previouslyComplete;
    prevCanCompleteRef.current = canComplete;

    const now = Date.now();
    const elapsed = now - lastProgressSyncRef.current;
    const shouldSync = becameComplete || elapsed >= PROGRESS_SAVE_INTERVAL_MS;

    if (!shouldSync) return;
    if (syncProgressInFlightRef.current) return;

    syncProgressInFlightRef.current = true;
    lastProgressSyncRef.current = now;

    (async () => {
      try {
        if (isMountedRef.current) {
          setSaving(true);
        }
        await http.put(`/trails/${trailId}/items/${detail.id}/progress`, {
          status: canComplete ? "COMPLETED" : "IN_PROGRESS",
          progress_value: Math.floor(watchedSeconds), // segundos assistidos
        });
        await loadProgress();
      } catch {
        // noop: manter UX silenciosa
      } finally {
        syncProgressInFlightRef.current = false;
        if (isMountedRef.current) {
          setSaving(false);
        }
      }
    })();
  }, [watchedSeconds, canComplete, trailId, detail, loadProgress]);

  if (loading || !progress) {
    return <div className="lesson-page loading">Carregando…</div>;
  }

  return (
    <Layout>
    <div className={`lesson-page${sidebarOpen ? " sidebar-open" : ""}${sidebarCollapsed ? " sidebar-collapsed" : ""}`}>
      {/* Sidebar */}
      <aside className="lesson-sidebar">
        <div className="sidebar-header">
          <span className="sidebar-title">Conteúdo do curso</span>
          <button
            type="button"
            className="sidebar-close-btn"
            onClick={handleSidebarClose}
            aria-label={isMobileView ? "Fechar menu de conteúdo" : sidebarCollapsed ? "Mostrar menu de conteúdo" : "Esconder menu de conteúdo"}
          >
            <X size={18} />
          </button>
        </div>

{sections.map((s) => {
  const isActive = s.items.some((i) => String(i.id) === itemId);
  const isOpen = openSections.has(s.id);
  const secProg = sectionProgress[s.id];
  const sectionSummary = secProg
    ? `${secProg.done}/${secProg.total} concluídos`
    : s.items.filter(i => i.type === "VIDEO").length
      ? `${s.items.filter(i => i.type === "VIDEO").length} vídeos`
      : `${s.items.length} itens`;

  return (
    <div key={s.id} className={`topic ${isActive ? "is-active" : ""}`}>
      <button
        type="button"
        className="topic-header"
        onClick={() => toggleSection(s.id)}
        aria-expanded={isOpen}
        aria-controls={`topic-body-${s.id}`}
      >
        <div className="topic-title">
          {s.title}
        </div>
        <div className="topic-summary">
          {sectionSummary}
        </div>
        <span className={`topic-caret ${isOpen ? "open" : ""}`} aria-hidden="true">▾</span>
      </button>

      <div
        id={`topic-body-${s.id}`}
        className={`topic-body ${isOpen ? "open" : ""}`}
      >
        {s.items.map((i) => {
          const progressInfo = itemProgress[i.id];
          const isDone = progressInfo?.status === "COMPLETED";
          const isCurrent = String(i.id) === itemId;
          const lockInfo = lockedItems[i.id] ?? null;
          const isLocked = Boolean(lockInfo);
          const lockTitle = lockInfo?.title?.trim() || "o item obrigatório";
          const lockHint = isLocked ? `Conclua ${lockTitle} antes de prosseguir.` : undefined;

          return (
            <Link
              key={i.id}
              to={`/trilha/${trailId}/aula/${i.id}`}
              className={`topic-item ${isCurrent ? "is-active" : ""} ${isDone ? "is-done" : ""} ${isLocked ? "is-locked" : ""}`}
              title={lockHint}
              aria-disabled={isLocked}
              onClick={handleSidebarItemClick}
            >
              <div className="left">
                <span className={`item-icon ${resolveIconClass(i.type)}`} />
                <span className="item-title">{i.title}</span>
              </div>
              <div className="right">
                {typeof i.duration_seconds === "number" && i.type !== "QUIZ" && (
                  <span className="item-duration">{fmtDuration(i.duration_seconds)}</span>
                )}
                {isLocked && (
                  <span className="item-status item-status-locked" aria-label={`Bloqueado até concluir ${lockTitle}`}>
                    Bloqueado
                  </span>
                )}
                {isDone && <span className="item-status" aria-label="Item concluído">✓</span>}
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
})} 

      </aside>
      <div
        className={`lesson-sidebar-overlay${sidebarOpen ? " open" : ""}`}
        onClick={handleSidebarClose}
        role="presentation"
      />

      {/* Main */}
      <main className="lesson-main">
        <button
          type="button"
          className="sidebar-toggle-btn"
          onClick={handleSidebarToggle}
          aria-expanded={isMobileView ? sidebarOpen : !sidebarCollapsed}
        >
          {isMobileView && sidebarOpen ? <X size={18} /> : <MenuIcon size={18} />}
          <span>
            {isMobileView
              ? sidebarOpen ? "Fechar menu" : "Conteúdo"
              : sidebarCollapsed ? "Mostrar menu" : "Esconder menu"}
          </span>
        </button>
        {blockedBy ? (
          <div className="lesson-locked" role="alert">
            <h2>Conteúdo bloqueado</h2>
            <p>
              Conclua <strong>{blockedTitle}</strong> antes de prosseguir.
            </p>
            {blockedTargetId ? (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => {
                  setBlockedBy(null);
                  navigate(`/trilha/${trailId}/aula/${blockedTargetId}`);
                }}
              >
                Ir para {blockedTitle}
              </button>
            ) : null}
          </div>
        ) : detail ? (
          <>
            <div className="topbar">
              <div className="crumb-title">{detail.title}</div>

              <div className="progress-wrap">
                <span className="muted">Seu Progresso:</span>
                <span className="strong">{progress.done}</span>
                <span className="muted">de</span>
                <span className="strong">{progress.total}</span>
                <span className="muted">
                  ({Math.round(progress.computed_progress_percent || 0)}%)
                </span>
              </div>

              {progress.status && (
                <span
                  className={`trail-status-badge status-${progress.status.toLowerCase()}`}
                >
                  {formatStatus(progress.status)}
                </span>
              )}

              {detail.type === "VIDEO" && (
                <span className="video-auto-note">O vídeo é concluído automaticamente ao atingir a porcentagem mínima.</span>
              )}

              {showManualCompletion && (
                <button
                  className="btn btn-primary mark-complete"
                  disabled={saving || progress.status === "COMPLETED"}
                  onClick={async () => {
                    try {
                      setSaving(true);
                      await http.put(`/trails/${trailId}/items/${detail.id}/progress`, {
                        status: "COMPLETED",
                        progress_value: detail.type === "VIDEO"
                          ? Math.floor(watchedSeconds)
                          : null,
                      });
                      await loadProgress();
                    } finally {
                      setSaving(false);
                    }
                  }}
                  title="Marcar como concluído"
                >
                  {saving ? "Salvando…" : "Marcar como concluído"}
                </button>
              )}

              {progress.status === "COMPLETED" && (
                <button
                  className="btn btn-secondary"
                  onClick={() => { void handleOpenCertificate(); }}
                  disabled={certLoading}
                >
                  {certLoading ? "Abrindo certificado…" : "Ver certificado"}
                </button>
              )}

            </div>
            {certError && (
              <div className="cert-error-inline" role="alert">
                {certError}
              </div>
            )}

            {detail.type === "VIDEO" && detail.youtubeId ? (
              <div className="video-wrapper">
                <YouTubePlayer
                  videoId={detail.youtubeId}
                  startAt={resumePositionRef.current}
                  playedSeconds={Math.max(maxWatched, watch.current, resumePositionRef.current)}
                  onReady={({ current, duration }) => {
                    setWatch({ current, duration });
                    setMaxWatched((prev) => Math.max(prev, current));
                  }}
                  onProgress={({ current, duration }) => {
                    setWatch({ current, duration });
                    setMaxWatched((prev) => Math.max(prev, current));
                  }}
                  maxAllowedPosition={maxSeekPosition}
                  seekBlockedLabel={seekBlockedLabel}
                />
                {!isPrivileged && (
                  <p className="video-note">
                    Você pode arrastar a linha do tempo apenas até o ponto já assistido.
                  </p>
                )}
              </div>
            ) : detail.type === "DOC" ? (
              <div className="doc-viewer">
                {detail.resource_kind === "PDF" && detail.resource_url ? (
                  <iframe
                    className="doc-frame"
                    src={detail.resource_url.includes("#") ? detail.resource_url : `${detail.resource_url}#toolbar=0`}
                    title={detail.title || "Pré-visualização do documento"}
                    loading="lazy"
                  />
                ) : detail.resource_kind === "IMAGE" && detail.resource_url ? (
                  <img
                    className="doc-image"
                    src={detail.resource_url}
                    alt={detail.title || "Pré-visualização da imagem"}
                    loading="lazy"
                  />
                ) : detail.resource_url ? (
                  <div className="doc-fallback">
                    <p>Conteúdo disponível no link abaixo.</p>
                  </div>
                ) : (
                  <div className="doc-fallback">
                    <p>Conteúdo não disponível para este item.</p>
                  </div>
                )}
                {detail.resource_url && (
                  <div className="doc-actions">
                    <a
                      className="btn btn-secondary"
                      href={detail.resource_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {detail.resource_kind === "PDF"
                        ? "Abrir PDF em nova guia"
                        : detail.resource_kind === "IMAGE"
                        ? "Abrir imagem em nova guia"
                        : "Abrir recurso em nova guia"}
                    </a>
                    <p className="doc-hint">
                      Caso o visualizador não carregue, abra o recurso em outra guia.
                    </p>
                  </div>
                )}
              </div>
            ) : detail.type === "FORM" && detail.form ? (
              <div className="form-wrapper">
                {detail.form.title && <h2 className="form-title">{detail.form.title}</h2>}
                {formResult && (
                  <div className={`form-result ${formResult.passed === false ? "is-fail" : ""}`}>
                    <strong>Resultado:</strong> {formResult.score.toFixed(2)}%
                    <span className="form-result-points">
                      ({formResult.score_points.toFixed(2)} / {formResult.max_points.toFixed(2)} pts)
                    </span>
                    {formResult.passed !== null && (
                      <span className="form-result-badge">{formResult.passed ? "Aprovado" : "Reprovado"}</span>
                    )}
                    {formResult.requires_manual_review && (
                      <p className="form-result-note">Esta tentativa aguarda correção manual.</p>
                    )}
                    {!formResult.requires_manual_review && detail.form && (
                      <p className="form-result-note">
                        Nota mínima para aprovação: {detail.form.min_score_to_pass.toFixed(2)}%
                      </p>
                    )}
                  </div>
                )}
                {formError && (
                  <div className="form-error" role="alert">
                    {formError}
                  </div>
                )}

                <form
                  className="trail-form"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void submitFormAnswers();
                  }}
                >
                  {detail.form.questions.length === 0 && (
                    <p className="question-note">Nenhuma questão configurada para este formulário.</p>
                  )}
                  {detail.form.questions.map((question) => {
                    const stored = formAnswers[question.id];
                    const result = questionResultMap.get(question.id);
                    const label = questionOrderMap.get(question.id) ?? question.order_index + 1;
                    return (
                      <fieldset
                        key={question.id}
                        className={`form-question ${result ? (result.is_correct === true ? "is-correct" : result.is_correct === false ? "is-incorrect" : "is-pending") : ""}`}
                      >
                        <legend>
                          <span className="question-index">Questão {label}</span>
                          {question.required && <span className="question-required">*</span>}
                        </legend>
                        <p className="question-prompt">{question.prompt}</p>

                        {question.type === "ESSAY" ? (
                          <textarea
                            value={stored?.answerText ?? ""}
                            onChange={(e) => handleEssayChange(question.id, e.target.value)}
                            rows={4}
                            placeholder="Digite sua resposta"
                          />
                        ) : (
                          <div className="question-options">
                            {question.options.map((option) => (
                              <label key={option.id} className="question-option">
                                <input
                                  type="radio"
                                  name={`question-${question.id}`}
                                  value={option.id}
                                  checked={stored?.selectedOptionId === option.id}
                                  onChange={() => handleOptionChange(question.id, option.id)}
                                />
                                <span>{option.text}</span>
                              </label>
                            ))}
                            {question.options.length === 0 && (
                              <p className="question-note">Opções não configuradas para esta questão.</p>
                            )}
                          </div>
                        )}

                        {result && (
                          <div className="question-feedback">
                            {result.is_correct === true && <span className="is-correct">Resposta correta (+{result.points_awarded ?? 0} pts)</span>}
                            {result.is_correct === false && <span className="is-incorrect">Resposta incorreta</span>}
                            {result.is_correct === null && <span className="is-pending">Avaliação pendente</span>}
                          </div>
                        )}
                      </fieldset>
                    );
                  })}

                  <button type="submit" className="btn btn-primary" disabled={formSubmitting}>
                    {formSubmitting ? "Enviando respostas…" : "Enviar respostas"}
                  </button>
                </form>
              </div>
            ) : (
              <div className="lesson-placeholder">Conteúdo não disponível para este item.</div>
            )}

            <section className="lesson-about">
              <h3>Sobre a Aula</h3>
              <div className="about-html" dangerouslySetInnerHTML={{ __html: detail.description_html }} />
            </section>

            <footer className="lesson-footer">
              <div className="footer-left">
                {detail.prev_item_id ? (
                  <Link className="btn btn-secondary btn-sm" to={`/trilha/${trailId}/aula/${detail.prev_item_id}`}>
                    <span className="icon-previous" />
                    <span>Anterior</span>
                  </Link>
                ) : (
                  <span />
                )}
              </div>
              <div className="footer-right">
                {detail.next_item_id ? (
                  <Link className="btn btn-secondary btn-sm" to={`/trilha/${trailId}/aula/${detail.next_item_id}`}>
                    <span>Próximo</span>
                    <span className="icon-next" />
                  </Link>
                ) : (
                  <span />
                )}
              </div>
            </footer>
          </>
        ) : (
          <div className="lesson-locked">
            <h2>Conteúdo indisponível</h2>
            <p>Não foi possível carregar esta aula. Tente novamente mais tarde.</p>
          </div>
        )}
      </main>
    </div>
    </Layout>
  );
}

/** helpers */
function pad(n: number) { return n < 10 ? `0${n}` : `${n}`; }
function fmtDuration(sec: number) {
  const s = Math.floor(sec % 60);
  const m = Math.floor((sec / 60) % 60);
  const h = Math.floor(sec / 3600);
  if (h > 0) return `${h}:${pad(m)}:${pad(s)}`;
  return `${pad(m)}:${pad(s)}`;
}

function formatStatus(status?: string | null) {
  if (!status) return "";
  const map: Record<string, string> = {
    COMPLETED: "Concluída",
    IN_PROGRESS: "Em andamento",
    ENROLLED: "Inscrito",
  };
  return map[status] ?? status;
}
