import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { ArrowDown, ArrowUp, Loader2, Plus, Trash2 } from "lucide-react";
import Layout from "../components/Layout";
import { useAuth } from "../hooks/useAuth";
import { http } from "../lib/http";
import "../styles/AdminPanel.css";

type DashboardSummary = {
  total_users: number;
  total_trails: number;
  total_enrollments: number;
  total_certificates: number;
};

type DashboardData = {
  summary: DashboardSummary;
  enrollment_by_status: Record<string, number>;
  recent_trails: Array<{
    id: number;
    name: string;
    created_date: string | null;
    sections: number;
    items: number;
  }>;
  recent_certificates: Array<{
    id: number;
    issued_at: string;
    user: string;
    trail: string;
  }>;
  top_trails: Array<{
    id: number;
    name: string;
    enrollments: number;
    completed: number;
  }>;
};

type AdminTrailSummary = {
  id: number;
  name: string;
  author: string | null;
  created_date: string | null;
};

type AdminTrailDetail = {
  id: number;
  name: string;
  thumbnail_url: string;
  description: string;
  author: string;
  sections: Array<{
    id: number;
    title: string;
    order_index: number;
    items: Array<{
      id: number;
      title: string;
      type: string;
      url: string;
      duration_seconds: number | null;
      requires_completion: boolean;
      order_index: number;
      form?: {
        id: number;
        title: string;
        description: string;
        min_score_to_pass: number;
        randomize_questions: boolean;
        questions: Array<{
          id: number;
          prompt: string;
          type: string;
          required: boolean;
          points: number;
          order_index: number;
          options: Array<{
            id: number;
            text: string;
            is_correct: boolean;
            order_index: number;
          }>;
        }>;
      };
    }>;
  }>;
};

type ItemTypeOption = { code: string; label: string };

type DraftFormOption = {
  id: string;
  text: string;
  isCorrect: boolean;
  order: number;
};

type DraftQuestionType = "ESSAY" | "TRUE_OR_FALSE" | "SINGLE_CHOICE";

type DraftFormQuestion = {
  id: string;
  prompt: string;
  type: DraftQuestionType;
  required: boolean;
  points: string;
  options: DraftFormOption[];
};

type DraftForm = {
  title: string;
  description: string;
  minScore: string;
  randomize: boolean;
  questions: DraftFormQuestion[];
};

type DraftItem = {
  id: string;
  title: string;
  type: string;
  content: string;
  duration: string;
  requiresCompletion: boolean;
  form?: DraftForm;
};

type DraftSection = {
  id: string;
  title: string;
  items: DraftItem[];
};

const DEFAULT_ITEM_TYPES: ItemTypeOption[] = [
  { code: "VIDEO", label: "Vídeo" },
  { code: "DOC", label: "Documento" },
  { code: "FORM", label: "Formulário" },
];

const DEFAULT_QUESTION_TYPES: ItemTypeOption[] = [
  { code: "ESSAY", label: "Dissertativa" },
  { code: "TRUE_OR_FALSE", label: "Verdadeiro ou falso" },
  { code: "SINGLE_CHOICE", label: "Múltipla escolha" },
];

function randomId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2, 10);
}

function normalizeError(err: unknown): string {
  if (typeof err === "string") return err;
  if (err && typeof err === "object") {
    const maybeAxios = err as { response?: { data?: any } };
    const detail = maybeAxios.response?.data?.detail;
    if (Array.isArray(detail) && detail.length && detail[0]?.msg) {
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

function createEmptySection(): DraftSection {
  return {
    id: randomId(),
    title: "",
    items: [],
  };
}

function createDefaultOptionsFor(type: DraftQuestionType): DraftFormOption[] {
  if (type === "TRUE_OR_FALSE") {
    return [
      { id: randomId(), text: "Verdadeiro", isCorrect: true, order: 0 },
      { id: randomId(), text: "Falso", isCorrect: false, order: 1 },
    ];
  }
  if (type === "SINGLE_CHOICE") {
    return [
      { id: randomId(), text: "Opção 1", isCorrect: true, order: 0 },
      { id: randomId(), text: "Opção 2", isCorrect: false, order: 1 },
    ];
  }
  return [];
}

function createEmptyQuestion(type: DraftQuestionType): DraftFormQuestion {
  return {
    id: randomId(),
    prompt: "",
    type,
    required: true,
    points: "1",
    options: createDefaultOptionsFor(type).map((option, index) => ({
      ...option,
      order: index,
    })),
  };
}

function ensureQuestionOptions(question: DraftFormQuestion): DraftFormQuestion {
  if (question.type === "ESSAY") {
    return { ...question, options: [] };
  }
  let options = question.options.map((option, index) => ({
    ...option,
    order: index,
  }));
  if (!options.length) {
    options = createDefaultOptionsFor(question.type).map((option, index) => ({
      ...option,
      order: index,
    }));
  }
  if (question.type === "TRUE_OR_FALSE") {
    const base = createDefaultOptionsFor("TRUE_OR_FALSE");
    options = base.map((option, index) => {
      const existing = question.options[index];
      return {
        ...option,
        id: existing?.id ?? option.id,
        isCorrect: index === 0 ? existing?.isCorrect ?? true : existing?.isCorrect ?? false,
        order: index,
      };
    });
  }
  return { ...question, options };
}

function createDefaultForm(): DraftForm {
  return {
    title: "",
    description: "",
    minScore: "70",
    randomize: false,
    questions: [createEmptyQuestion("SINGLE_CHOICE")],
  };
}

function parseNumericInput(value: string, fallback: number): number {
  if (!value) return fallback;
  const normalized = value.replace(/,/g, ".");
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function toDraftQuestionType(value: string): DraftQuestionType {
  const normalized = (value || "").toUpperCase();
  if (normalized === "ESSAY" || normalized === "TRUE_OR_FALSE" || normalized === "SINGLE_CHOICE") {
    return normalized as DraftQuestionType;
  }
  return "SINGLE_CHOICE";
}

export default function AdminPanel() {
  const { user, loading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<"dashboard" | "builder">("dashboard");

  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardLoaded, setDashboardLoaded] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  const [itemTypes, setItemTypes] = useState<ItemTypeOption[]>([]);
  const [questionTypes, setQuestionTypes] = useState<ItemTypeOption[]>([]);

  const [existingTrails, setExistingTrails] = useState<AdminTrailSummary[]>([]);
  const [existingTrailsLoading, setExistingTrailsLoading] = useState(false);
  const [existingTrailsLoaded, setExistingTrailsLoaded] = useState(false);
  const [existingTrailsError, setExistingTrailsError] = useState<string | null>(null);
  const [selectedTrailId, setSelectedTrailId] = useState<string>("");
  const [editingTrailId, setEditingTrailId] = useState<number | null>(null);
  const [loadingTrail, setLoadingTrail] = useState(false);
  const trailsRequestInFlight = useRef(false);

  const [name, setName] = useState("");
  const [thumbnailUrl, setThumbnailUrl] = useState("");
  const [author, setAuthor] = useState("");
  const [description, setDescription] = useState("");
  const [sections, setSections] = useState<DraftSection[]>([createEmptySection()]);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const isEditing = editingTrailId !== null;

  const isAdmin = user?.role === "Admin";
  const availableItemTypes = useMemo(
    () => (itemTypes.length ? itemTypes : DEFAULT_ITEM_TYPES),
    [itemTypes]
  );
  const availableQuestionTypes = useMemo(
    () => (questionTypes.length ? questionTypes : DEFAULT_QUESTION_TYPES),
    [questionTypes]
  );

  useEffect(() => {
    if (authLoading || !isAdmin) return;
    let cancelled = false;
    const loadItemTypes = async () => {
      try {
        const { data } = await http.get<{ item_types: ItemTypeOption[] }>("/admin/trails/item-types");
        if (!cancelled) {
          setItemTypes(data.item_types ?? []);
        }
      } catch {
        if (!cancelled) {
          setItemTypes([]);
        }
      }
    };
    const loadQuestionTypes = async () => {
      try {
        const { data } = await http.get<{ question_types: ItemTypeOption[] }>("/admin/forms/question-types");
        if (!cancelled) {
          setQuestionTypes(data.question_types ?? []);
        }
      } catch {
        if (!cancelled) {
          setQuestionTypes([]);
        }
      }
    };
    void loadItemTypes();
    void loadQuestionTypes();
    return () => {
      cancelled = true;
    };
  }, [authLoading, isAdmin]);

  useEffect(() => {
    if (authLoading || !isAdmin) return;
    if (activeTab !== "builder") return;
    if (existingTrailsLoaded || trailsRequestInFlight.current) return;
    let cancelled = false;
    const loadTrails = async () => {
      trailsRequestInFlight.current = true;
      setExistingTrailsLoading(true);
      setExistingTrailsError(null);
      try {
        const { data } = await http.get<{ trails: AdminTrailSummary[] }>("/admin/trails");
        if (!cancelled) {
          setExistingTrails(data.trails ?? []);
        }
      } catch (err) {
        if (!cancelled) {
          setExistingTrails([]);
          setExistingTrailsError(normalizeError(err));
        }
      } finally {
        if (!cancelled) {
          setExistingTrailsLoaded(true);
          setExistingTrailsLoading(false);
        }
        trailsRequestInFlight.current = false;
      }
    };
    void loadTrails();
    return () => {
      cancelled = true;
      trailsRequestInFlight.current = false;
      setExistingTrailsLoading(false);
    };
  }, [activeTab, authLoading, existingTrailsLoaded, isAdmin]);

  useEffect(() => {
    if (authLoading || !isAdmin) return;
    if (activeTab !== "dashboard") return;
    if (dashboardLoaded) return;
    let cancelled = false;
    const loadDashboard = async () => {
      setDashboardLoading(true);
      setDashboardError(null);
      try {
        const { data } = await http.get<DashboardData>("/admin/dashboard");
        if (!cancelled) {
          setDashboard(data);
          setDashboardLoaded(true);
        }
      } catch (err) {
        if (!cancelled) {
          setDashboardError(normalizeError(err));
        }
      } finally {
        if (!cancelled) setDashboardLoading(false);
      }
    };
    void loadDashboard();
    return () => {
      cancelled = true;
    };
  }, [activeTab, authLoading, dashboardLoaded, isAdmin]);

  const resetBuilder = () => {
    setName("");
    setThumbnailUrl("");
    setAuthor("");
    setDescription("");
    setSections([createEmptySection()]);
    setSelectedTrailId("");
    setEditingTrailId(null);
  };

  const applyTrailToBuilder = (trail: AdminTrailDetail) => {
    setName(trail.name ?? "");
    setThumbnailUrl(trail.thumbnail_url ?? "");
    setAuthor(trail.author ?? "");
    setDescription(trail.description ?? "");
    const mappedSections = trail.sections.length
      ? trail.sections.map((section) => ({
          id: randomId(),
          title: section.title ?? "",
          items: section.items.map((item) => {
            const baseItem: DraftItem = {
              id: randomId(),
              title: item.title ?? "",
              type: (item.type || "VIDEO").toUpperCase(),
              content: item.url ?? "",
              duration: item.duration_seconds != null ? String(item.duration_seconds) : "",
              requiresCompletion: Boolean(item.requires_completion),
              form: undefined,
            };
            if (baseItem.type === "FORM" && item.form) {
              const questions = item.form.questions.map((question) => {
                const questionType = toDraftQuestionType(question.type);
                const draftQuestion: DraftFormQuestion = {
                  id: randomId(),
                  prompt: question.prompt ?? "",
                  type: questionType,
                  required: Boolean(question.required),
                  points: String(question.points ?? 0),
                  options:
                    questionType === "ESSAY"
                      ? []
                      : question.options.map((option) => ({
                          id: randomId(),
                          text: option.text ?? "",
                          isCorrect: option.is_correct,
                          order: option.order_index ?? 0,
                        })),
                };
                return ensureQuestionOptions(draftQuestion);
              });
              baseItem.form = {
                title: item.form.title ?? "",
                description: item.form.description ?? "",
                minScore: String(item.form.min_score_to_pass ?? 70),
                randomize: Boolean(item.form.randomize_questions),
                questions,
              };
            }
            return baseItem;
          }),
        }))
      : [createEmptySection()];
    setSections(mappedSections);
    setEditingTrailId(trail.id);
    setSelectedTrailId(String(trail.id));
    setSaveError(null);
    setSaveSuccess(null);
  };

  const loadTrailForEdit = async (trailId: number) => {
    setLoadingTrail(true);
    setSaveError(null);
    setSaveSuccess(null);
    setExistingTrailsError(null);
    try {
      const { data } = await http.get<{ trail: AdminTrailDetail }>(`/admin/trails/${trailId}`);
      applyTrailToBuilder(data.trail);
    } catch (err) {
      setSaveError(normalizeError(err));
    } finally {
      setLoadingTrail(false);
    }
  };

  const handleLoadSelectedTrail = () => {
    if (!selectedTrailId) return;
    const trailId = Number(selectedTrailId);
    if (!Number.isFinite(trailId)) return;
    void loadTrailForEdit(trailId);
  };

  const handleStartNewTrail = () => {
    setSaveError(null);
    setSaveSuccess(null);
    setExistingTrailsError(null);
    resetBuilder();
  };

  const addSection = () => {
    setSections((prev) => [...prev, createEmptySection()]);
  };

  const removeSection = (sectionId: string) => {
    setSections((prev) => prev.filter((section) => section.id !== sectionId));
  };

  const moveSection = (sectionId: string, direction: -1 | 1) => {
    setSections((prev) => {
      const index = prev.findIndex((section) => section.id === sectionId);
      if (index < 0) return prev;
      const targetIndex = index + direction;
      if (targetIndex < 0 || targetIndex >= prev.length) return prev;
      const next = [...prev];
      const [current] = next.splice(index, 1);
      next.splice(targetIndex, 0, current);
      return next;
    });
  };

  const updateSectionTitle = (sectionId: string, value: string) => {
    setSections((prev) =>
      prev.map((section) =>
        section.id === sectionId ? { ...section, title: value } : section
      )
    );
  };

  const addItem = (sectionId: string) => {
    const defaultType = availableItemTypes[0]?.code ?? "VIDEO";
    setSections((prev) =>
      prev.map((section) =>
        section.id === sectionId
          ? {
              ...section,
              items: [
                ...section.items,
                {
                  id: randomId(),
                  title: "",
                  type: defaultType,
                  content: "",
                  duration: "",
                  requiresCompletion: false,
                  form: defaultType === "FORM" ? createDefaultForm() : undefined,
                },
              ],
            }
          : section
      )
    );
  };

  const removeItem = (sectionId: string, itemId: string) => {
    setSections((prev) =>
      prev.map((section) =>
        section.id === sectionId
          ? { ...section, items: section.items.filter((item) => item.id !== itemId) }
          : section
      )
    );
  };

  const moveItem = (sectionId: string, itemId: string, direction: -1 | 1) => {
    setSections((prev) =>
      prev.map((section) => {
        if (section.id !== sectionId) return section;
        const index = section.items.findIndex((item) => item.id === itemId);
        if (index < 0) return section;
        const targetIndex = index + direction;
        if (targetIndex < 0 || targetIndex >= section.items.length) return section;
        const nextItems = [...section.items];
        const [current] = nextItems.splice(index, 1);
        nextItems.splice(targetIndex, 0, current);
        return { ...section, items: nextItems };
      })
    );
  };

  const updateItem = (
    sectionId: string,
    itemId: string,
    patch: Partial<Omit<DraftItem, "id">>
  ) => {
    setSections((prev) =>
      prev.map((section) => {
        if (section.id !== sectionId) return section;
        const nextItems = section.items.map((item) => {
          if (item.id !== itemId) return item;
          const nextType = patch.type ?? item.type;
          const ensureForm =
            nextType === "FORM"
              ? item.form ?? createDefaultForm()
              : undefined;
          const merged: DraftItem = {
            ...item,
            ...patch,
            form: ensureForm,
          };
          if (merged.form && merged.type === "FORM") {
            merged.form = {
              ...merged.form,
              questions: merged.form.questions.map((question) => {
                const ensured = ensureQuestionOptions(question);
                return {
                  ...ensured,
                  points: ensured.points || "1",
                };
              }),
            };
          }
          return merged;
        });
        return { ...section, items: nextItems };
      })
    );
  };

  const setFormState = (
    sectionId: string,
    itemId: string,
    updater: (form: DraftForm) => DraftForm
  ) => {
    setSections((prev) =>
      prev.map((section) => {
        if (section.id !== sectionId) return section;
        const nextItems = section.items.map((item) => {
          if (item.id !== itemId) return item;
          if (item.type !== "FORM" || !item.form) return item;
          const nextForm = updater(item.form);
          const ensuredQuestions = (
            nextForm.questions.length ? nextForm.questions : [createEmptyQuestion("SINGLE_CHOICE")]
          ).map((question) => ensureQuestionOptions(question));
          return {
            ...item,
            form: {
              ...nextForm,
              questions: ensuredQuestions,
            },
          };
        });
        return { ...section, items: nextItems };
      })
    );
  };

  const updateFormMeta = (
    sectionId: string,
    itemId: string,
    patch: Partial<Omit<DraftForm, "questions">>
  ) => {
    setFormState(sectionId, itemId, (form) => ({ ...form, ...patch }));
  };

  const addQuestion = (sectionId: string, itemId: string, type: DraftQuestionType) => {
    setFormState(sectionId, itemId, (form) => ({
      ...form,
      questions: [...form.questions, createEmptyQuestion(type)],
    }));
  };

  const removeQuestion = (sectionId: string, itemId: string, questionId: string) => {
    setFormState(sectionId, itemId, (form) => ({
      ...form,
      questions: form.questions.filter((question) => question.id !== questionId),
    }));
  };

  const moveQuestion = (
    sectionId: string,
    itemId: string,
    questionId: string,
    direction: -1 | 1
  ) => {
    setFormState(sectionId, itemId, (form) => {
      const index = form.questions.findIndex((question) => question.id === questionId);
      if (index < 0) return form;
      const targetIndex = index + direction;
      if (targetIndex < 0 || targetIndex >= form.questions.length) return form;
      const nextQuestions = [...form.questions];
      const [current] = nextQuestions.splice(index, 1);
      nextQuestions.splice(targetIndex, 0, current);
      return { ...form, questions: nextQuestions };
    });
  };

  const updateQuestion = (
    sectionId: string,
    itemId: string,
    questionId: string,
    patch: Partial<Omit<DraftFormQuestion, "id" | "options">> & { options?: DraftFormOption[] }
  ) => {
    setFormState(sectionId, itemId, (form) => ({
      ...form,
      questions: form.questions.map((question) => {
        if (question.id !== questionId) return question;
        const nextType = (patch.type ?? question.type) as DraftQuestionType;
        const base: DraftFormQuestion = {
          ...question,
          ...patch,
          type: nextType,
        };
        return ensureQuestionOptions(base);
      }),
    }));
  };

  const addOption = (sectionId: string, itemId: string, questionId: string) => {
    setFormState(sectionId, itemId, (form) => ({
      ...form,
      questions: form.questions.map((question) => {
        if (question.id !== questionId) return question;
        if (question.type === "ESSAY" || question.type === "TRUE_OR_FALSE") return question;
        const nextOptions = [
          ...question.options,
          { id: randomId(), text: `Opção ${question.options.length + 1}`, isCorrect: false, order: question.options.length },
        ];
        return { ...question, options: nextOptions };
      }),
    }));
  };

  const moveOption = (
    sectionId: string,
    itemId: string,
    questionId: string,
    optionId: string,
    direction: -1 | 1
  ) => {
    setFormState(sectionId, itemId, (form) => ({
      ...form,
      questions: form.questions.map((question) => {
        if (question.id !== questionId) return question;
        if (question.type === "ESSAY" || question.type === "TRUE_OR_FALSE") return question;
        const index = question.options.findIndex((option) => option.id === optionId);
        if (index < 0) return question;
        const targetIndex = index + direction;
        if (targetIndex < 0 || targetIndex >= question.options.length) return question;
        const nextOptions = [...question.options];
        const [current] = nextOptions.splice(index, 1);
        nextOptions.splice(targetIndex, 0, current);
        return { ...question, options: nextOptions };
      }),
    }));
  };

  const removeOption = (
    sectionId: string,
    itemId: string,
    questionId: string,
    optionId: string
  ) => {
    setFormState(sectionId, itemId, (form) => ({
      ...form,
      questions: form.questions.map((question) => {
        if (question.id !== questionId) return question;
        const filtered = question.options.filter((option) => option.id !== optionId);
        return ensureQuestionOptions({ ...question, options: filtered });
      }),
    }));
  };

  const updateOption = (
    sectionId: string,
    itemId: string,
    questionId: string,
    optionId: string,
    patch: Partial<Omit<DraftFormOption, "id" | "order">>
  ) => {
    setFormState(sectionId, itemId, (form) => ({
      ...form,
      questions: form.questions.map((question) => {
        if (question.id !== questionId) return question;
        const nextOptions = question.options.map((option) =>
          option.id === optionId ? { ...option, ...patch } : option
        );
        return { ...question, options: nextOptions };
      }),
    }));
  };

  const setCorrectOption = (
    sectionId: string,
    itemId: string,
    questionId: string,
    optionId: string
  ) => {
    setFormState(sectionId, itemId, (form) => ({
      ...form,
      questions: form.questions.map((question) => {
        if (question.id !== questionId) return question;
        if (question.type === "ESSAY") return question;
        const nextOptions = question.options.map((option) => ({
          ...option,
          isCorrect: option.id === optionId,
        }));
        return { ...question, options: nextOptions };
      }),
    }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaveError(null);
    setSaveSuccess(null);
    setExistingTrailsError(null);

    const trimmedName = name.trim();
    const trimmedThumbnail = thumbnailUrl.trim();

    if (!trimmedName) {
      setSaveError("Informe o nome da rota.");
      return;
    }
    if (!trimmedThumbnail) {
      setSaveError("Informe a URL da capa da rota.");
      return;
    }
    if (!sections.length) {
      setSaveError("Adicione pelo menos uma seção.");
      return;
    }

    for (let sectionIndex = 0; sectionIndex < sections.length; sectionIndex += 1) {
      const section = sections[sectionIndex];
      const sectionTitle = section.title.trim();
      if (!sectionTitle) {
        setSaveError(`Informe um título para a seção ${sectionIndex + 1}.`);
        return;
      }
      if (!section.items.length) {
        setSaveError(`Adicione pelo menos um item na seção ${sectionIndex + 1}.`);
        return;
      }
      for (let itemIndex = 0; itemIndex < section.items.length; itemIndex += 1) {
        const item = section.items[itemIndex];
        const itemTitle = item.title.trim();
        if (!itemTitle) {
          setSaveError(`Informe o título do item ${itemIndex + 1} na seção ${sectionIndex + 1}.`);
          return;
        }
        const itemContent = item.content.trim();
        if (!itemContent) {
          setSaveError(`Informe o conteúdo/URL do item ${itemIndex + 1} na seção ${sectionIndex + 1}.`);
          return;
        }
        if (item.duration) {
          const parsedDuration = Number(item.duration);
          if (!Number.isFinite(parsedDuration) || parsedDuration < 0) {
            setSaveError(`Informe uma duração válida para o item ${itemIndex + 1} na seção ${sectionIndex + 1}.`);
            return;
          }
        }
        if (item.type === "FORM") {
          const form = item.form;
          if (!form) {
            setSaveError(`Configure o formulário do item ${itemIndex + 1} na seção ${sectionIndex + 1}.`);
            return;
          }
          const minScoreValue = parseNumericInput(form.minScore, 70);
          if (!Number.isFinite(minScoreValue) || minScoreValue < 0) {
            setSaveError(`Informe uma nota mínima válida no formulário da seção ${sectionIndex + 1}.`);
            return;
          }
          if (!form.questions.length) {
            setSaveError(`Adicione pelo menos uma pergunta ao formulário na seção ${sectionIndex + 1}.`);
            return;
          }
          for (let questionIndex = 0; questionIndex < form.questions.length; questionIndex += 1) {
            const question = form.questions[questionIndex];
            const prompt = question.prompt.trim();
            if (!prompt) {
              setSaveError(`Informe o enunciado da pergunta ${questionIndex + 1} no formulário da seção ${sectionIndex + 1}.`);
              return;
            }
            const pointsValue = parseNumericInput(question.points, 0);
            if (!Number.isFinite(pointsValue) || pointsValue < 0) {
              setSaveError(`Informe um valor de pontos válido na pergunta ${questionIndex + 1}.`);
              return;
            }
            if (question.type !== "ESSAY") {
              if (!question.options.length) {
                setSaveError(`Adicione alternativas para a pergunta ${questionIndex + 1}.`);
                return;
              }
              const trimmedOptions = question.options.map((option) => option.text.trim());
              if (trimmedOptions.some((text) => !text)) {
                setSaveError(`Preencha o texto de todas as alternativas na pergunta ${questionIndex + 1}.`);
                return;
              }
              const correctCount = question.options.filter((option) => option.isCorrect).length;
              if (correctCount === 0) {
                setSaveError(`Escolha uma alternativa correta na pergunta ${questionIndex + 1}.`);
                return;
              }
              if (question.type === "TRUE_OR_FALSE" && question.options.length !== 2) {
                setSaveError(`A pergunta ${questionIndex + 1} deve possuir duas alternativas (verdadeiro/falso).`);
                return;
              }
            }
          }
        }
      }
    }

    const payload = {
      name: trimmedName,
      thumbnail_url: trimmedThumbnail,
      author: author.trim() || null,
      description: description.trim() || null,
      sections: sections.map((section, sectionIndex) => ({
        title: section.title.trim(),
        order_index: sectionIndex,
        items: section.items.map((item, itemIndex) => ({
          title: item.title.trim(),
          type: item.type,
          url: item.content.trim(),
          duration_seconds: item.duration ? Number(item.duration) : null,
          requires_completion: item.requiresCompletion,
          order_index: itemIndex,
          form:
            item.type === "FORM" && item.form
              ? {
                  title: item.form.title.trim() || null,
                  description: item.form.description.trim() || null,
                  min_score_to_pass: parseNumericInput(item.form.minScore, 70),
                  randomize_questions: item.form.randomize,
                  questions: item.form.questions.map((question, questionIndex) => ({
                    prompt: question.prompt.trim(),
                    type: question.type,
                    required: question.required,
                    points: parseNumericInput(question.points, 0),
                    order_index: questionIndex,
                    options:
                      question.type === "ESSAY"
                        ? []
                        : question.options.map((option, optionIndex) => ({
                            text: option.text.trim(),
                            is_correct: option.isCorrect,
                            order_index: optionIndex,
                          })),
                  })),
                }
              : undefined,
        })),
      })),
    };

    setSaving(true);
    try {
      if (isEditing && editingTrailId) {
        await http.put(`/admin/trails/${editingTrailId}`, payload);
        setSaveSuccess("Rota atualizada com sucesso!");
      } else {
        await http.post("/admin/trails", payload);
        setSaveSuccess("Rota criada com sucesso!");
        resetBuilder();
      }
      setExistingTrailsLoaded(false);
      setExistingTrailsError(null);
      setDashboardLoaded(false);
    } catch (err) {
      setSaveError(normalizeError(err));
    } finally {
      setSaving(false);
    }
  };

  const refreshDashboard = () => {
    setDashboardLoaded(false);
  };

  if (authLoading) {
    return (
      <Layout>
        <section className="admin-panel">
          <div className="admin-feedback-card">Carregando…</div>
        </section>
      </Layout>
    );
  }

  if (!isAdmin) {
    return (
      <Layout>
        <section className="admin-panel">
          <div className="admin-feedback-card is-error">
            <h2>Acesso restrito</h2>
            <p>Somente administradores podem acessar este painel.</p>
          </div>
        </section>
      </Layout>
    );
  }

  const statusEntries = Object.entries(dashboard?.enrollment_by_status ?? {});

  return (
    <Layout>
      <section className="admin-panel">
        <header className="admin-header">
          <h1>Painel Administrativo</h1>
          <p>Gerencie as rotas e acompanhe indicadores da plataforma.</p>
        </header>

        <div className="admin-tabs">
          <button
            type="button"
            className={`admin-tab ${activeTab === "dashboard" ? "is-active" : ""}`}
            onClick={() => setActiveTab("dashboard")}
          >
            Dashboard
          </button>
          <button
            type="button"
            className={`admin-tab ${activeTab === "builder" ? "is-active" : ""}`}
            onClick={() => setActiveTab("builder")}
          >
            Criar rota
          </button>
        </div>

        {activeTab === "dashboard" ? (
          <div className="admin-dashboard">
            <div className="admin-dashboard-actions">
              <button
                type="button"
                className="admin-btn admin-btn-secondary"
                onClick={refreshDashboard}
                disabled={dashboardLoading}
              >
                {dashboardLoading ? <Loader2 size={16} className="spin" /> : null}
                Atualizar
              </button>
            </div>
            {dashboardError ? (
              <div className="admin-alert is-error">{dashboardError}</div>
            ) : null}
            <div className="admin-summary-grid">
              <div className="admin-summary-card">
                <span>Total de usuários</span>
                <strong>{dashboard?.summary.total_users ?? 0}</strong>
              </div>
              <div className="admin-summary-card">
                <span>Rotas publicadas</span>
                <strong>{dashboard?.summary.total_trails ?? 0}</strong>
              </div>
              <div className="admin-summary-card">
                <span>Matrículas</span>
                <strong>{dashboard?.summary.total_enrollments ?? 0}</strong>
              </div>
              <div className="admin-summary-card">
                <span>Certificados emitidos</span>
                <strong>{dashboard?.summary.total_certificates ?? 0}</strong>
              </div>
            </div>

            <div className="admin-grid">
              <section className="admin-card">
                <header>
                  <h2>Matrículas por status</h2>
                </header>
                {statusEntries.length ? (
                  <ul className="admin-status-list">
                    {statusEntries.map(([code, count]) => (
                      <li key={code}>
                        <span>{code}</span>
                        <strong>{count}</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="admin-empty">Nenhuma matrícula registrada.</p>
                )}
              </section>

              <section className="admin-card">
                <header>
                  <h2>Top rotas por matrículas</h2>
                </header>
                {dashboard?.top_trails.length ? (
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Rota</th>
                        <th>Matrículas</th>
                        <th>Concluídas</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.top_trails.map((trail) => (
                        <tr key={trail.id}>
                          <td>{trail.name}</td>
                          <td>{trail.enrollments}</td>
                          <td>{trail.completed}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="admin-empty">Ainda não há dados suficientes.</p>
                )}
              </section>
            </div>

            <div className="admin-grid">
              <section className="admin-card">
                <header>
                  <h2>Rotas recentes</h2>
                </header>
                {dashboard?.recent_trails.length ? (
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Rota</th>
                        <th>Seções</th>
                        <th>Itens</th>
                        <th>Criada em</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.recent_trails.map((trail) => (
                        <tr key={trail.id}>
                          <td>{trail.name}</td>
                          <td>{trail.sections}</td>
                          <td>{trail.items}</td>
                          <td>{trail.created_date ? new Date(trail.created_date).toLocaleDateString() : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="admin-empty">Nenhuma rota cadastrada ainda.</p>
                )}
              </section>

              <section className="admin-card">
                <header>
                  <h2>Últimos certificados</h2>
                </header>
                {dashboard?.recent_certificates.length ? (
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Aluno</th>
                        <th>Rota</th>
                        <th>Emitido em</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.recent_certificates.map((cert) => (
                        <tr key={cert.id}>
                          <td>{cert.user}</td>
                          <td>{cert.trail}</td>
                          <td>{new Date(cert.issued_at).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="admin-empty">Nenhum certificado emitido.</p>
                )}
              </section>
            </div>
          </div>
        ) : (
          <form className="admin-builder" onSubmit={handleSubmit}>
            <div className="admin-builder-toolbar">
              <div className="admin-builder-toolbar-group">
                <label>
                  <span>Editar rota existente</span>
                  <select
                    value={selectedTrailId}
                    onChange={(event) => setSelectedTrailId(event.target.value)}
                    disabled={existingTrailsLoading}
                  >
                    <option value="">Selecione uma rota</option>
                    {existingTrails.map((trail) => (
                      <option key={trail.id} value={trail.id}>
                        {trail.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="admin-builder-toolbar-actions">
                <button
                  type="button"
                  className="admin-btn admin-btn-secondary"
                  onClick={handleLoadSelectedTrail}
                  disabled={!selectedTrailId || loadingTrail}
                >
                  {loadingTrail ? <Loader2 size={16} className="spin" /> : null}
                  {isEditing && selectedTrailId === String(editingTrailId) ? "Recarregar" : "Carregar"}
                </button>
                <button
                  type="button"
                  className="admin-btn admin-btn-ghost"
                  onClick={handleStartNewTrail}
                  disabled={loadingTrail || saving}
                >
                  Nova rota
                </button>
              </div>
            </div>
            {isEditing ? (
              <div className="admin-builder-status">
                Editando: {name.trim() || `Rota #${editingTrailId}`}
              </div>
            ) : null}
            {existingTrailsError ? (
              <div className="admin-alert is-error">{existingTrailsError}</div>
            ) : null}
            {existingTrailsLoaded && !existingTrailsError && !existingTrails.length ? (
              <div className="admin-hint">Nenhuma rota cadastrada ainda.</div>
            ) : null}
            <section className="admin-card">
              <header>
                <h2>Informações básicas</h2>
                <p>
                  {isEditing
                    ? "Atualize os dados da rota selecionada."
                    : "Defina os principais dados da nova rota."}
                </p>
              </header>
              <div className="admin-form-grid">
                <label>
                  <span>Nome da rota *</span>
                  <input
                    type="text"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="Ex.: Trilha de Empreendedorismo"
                  />
                </label>
                <label>
                  <span>Autor</span>
                  <input
                    type="text"
                    value={author}
                    onChange={(event) => setAuthor(event.target.value)}
                    placeholder="Nome do autor"
                  />
                </label>
                <label className="full">
                  <span>URL da imagem de capa *</span>
                  <input
                    type="url"
                    value={thumbnailUrl}
                    onChange={(event) => setThumbnailUrl(event.target.value)}
                    placeholder="https://..."
                  />
                </label>
                <label className="full">
                  <span>Descrição</span>
                  <textarea
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    placeholder="Explique rapidamente o objetivo da rota."
                  ></textarea>
                </label>
              </div>
            </section>

            <section className="admin-card">
              <header className="admin-card-header">
                <div>
                  <h2>Seções e itens</h2>
                  <p>Monte o conteúdo da rota e organize a ordem desejada.</p>
                </div>
                <button
                  type="button"
                  className="admin-btn admin-btn-secondary"
                  onClick={addSection}
                >
                  <Plus size={16} />
                  Nova seção
                </button>
              </header>

              <div className="admin-section-list">
                {sections.map((section, index) => (
                  <div className="admin-section-card" key={section.id}>
                    <div className="admin-section-header">
                      <label>
                        <span>Nome da seção</span>
                        <input
                          type="text"
                          value={section.title}
                          onChange={(event) => updateSectionTitle(section.id, event.target.value)}
                          placeholder={`Seção ${index + 1}`}
                        />
                      </label>
                      <div className="admin-section-actions">
                        <button
                          type="button"
                          className="icon-btn"
                          onClick={() => moveSection(section.id, -1)}
                          disabled={index === 0}
                          aria-label="Mover seção para cima"
                        >
                          <ArrowUp size={16} />
                        </button>
                        <button
                          type="button"
                          className="icon-btn"
                          onClick={() => moveSection(section.id, 1)}
                          disabled={index === sections.length - 1}
                          aria-label="Mover seção para baixo"
                        >
                          <ArrowDown size={16} />
                        </button>
                        <button
                          type="button"
                          className="icon-btn danger"
                          onClick={() => removeSection(section.id)}
                          aria-label="Remover seção"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>

                    <div className="admin-item-list">
                      {section.items.map((item, itemIndex) => (
                        <div className="admin-item-card" key={item.id}>
                          <div className="admin-item-grid">
                            <label className="full">
                              <span>Título do item</span>
                              <input
                                type="text"
                                value={item.title}
                                onChange={(event) =>
                                  updateItem(section.id, item.id, { title: event.target.value })
                                }
                                placeholder={`Item ${itemIndex + 1}`}
                              />
                            </label>
                            <label>
                              <span>Tipo</span>
                              <select
                                value={item.type}
                                onChange={(event) =>
                                  updateItem(section.id, item.id, { type: event.target.value })
                                }
                              >
                                {availableItemTypes.map((option) => (
                                  <option key={option.code} value={option.code}>
                                    {option.label}
                                  </option>
                                ))}
                              </select>
                            </label>
                            <label>
                              <span>Duração (segundos)</span>
                              <input
                                type="number"
                                min={0}
                                value={item.duration}
                                onChange={(event) =>
                                  updateItem(section.id, item.id, { duration: event.target.value })
                                }
                              />
                            </label>
                            <label className="full">
                              <span>Conteúdo / URL</span>
                              <input
                                type="text"
                                value={item.content}
                                onChange={(event) =>
                                  updateItem(section.id, item.id, { content: event.target.value })
                                }
                                placeholder="Link ou identificador do conteúdo"
                              />
                            </label>

                            <label className="checkbox">
                              <input
                                type="checkbox"
                                checked={item.requiresCompletion}
                                onChange={(event) =>
                                  updateItem(section.id, item.id, {
                                    requiresCompletion: event.target.checked,
                                  })
                                }
                              />
                              <span>Item obrigatório</span>
                            </label>
                          </div>
                          {item.type === "FORM" && item.form ? (
                            <div className="admin-form-builder">
                              <div className="admin-form-meta">
                                <label>
                                  <span>Título do formulário</span>
                                  <input
                                    type="text"
                                    value={item.form.title}
                                    onChange={(event) =>
                                      updateFormMeta(section.id, item.id, { title: event.target.value })
                                    }
                                    placeholder="Nome exibido no formulário"
                                  />
                                </label>
                                <label className="full">
                                  <span>Descrição</span>
                                  <textarea
                                    value={item.form.description}
                                    onChange={(event) =>
                                      updateFormMeta(section.id, item.id, { description: event.target.value })
                                    }
                                    placeholder="Instruções para os participantes"
                                  ></textarea>
                                </label>
                                <label>
                                  <span>Nota mínima para aprovação</span>
                                  <input
                                    type="number"
                                    min={0}
                                    step={0.5}
                                    value={item.form.minScore}
                                    onChange={(event) =>
                                      updateFormMeta(section.id, item.id, { minScore: event.target.value })
                                    }
                                  />
                                </label>
                                <label className="checkbox-inline">
                                  <input
                                    type="checkbox"
                                    checked={item.form.randomize}
                                    onChange={(event) =>
                                      updateFormMeta(section.id, item.id, { randomize: event.target.checked })
                                    }
                                  />
                                  <span>Embaralhar ordem das perguntas</span>
                                </label>
                              </div>

                              <div className="admin-question-list">
                                {item.form.questions.map((question, questionIndex) => {
                                  const totalQuestions = item.form?.questions.length ?? 0;
                                  return (
                                    <div className="admin-question-card" key={question.id}>
                                      <div className="admin-question-header">
                                        <div>
                                          <h4>Pergunta {questionIndex + 1}</h4>
                                        </div>
                                        <div className="admin-question-actions">
                                          <button
                                            type="button"
                                            className="icon-btn"
                                            onClick={() => moveQuestion(section.id, item.id, question.id, -1)}
                                            disabled={questionIndex === 0}
                                            aria-label="Mover pergunta para cima"
                                          >
                                            <ArrowUp size={16} />
                                          </button>
                                          <button
                                            type="button"
                                            className="icon-btn"
                                            onClick={() => moveQuestion(section.id, item.id, question.id, 1)}
                                            disabled={questionIndex === totalQuestions - 1}
                                            aria-label="Mover pergunta para baixo"
                                          >
                                            <ArrowDown size={16} />
                                          </button>
                                          <button
                                            type="button"
                                            className="icon-btn danger"
                                            onClick={() => removeQuestion(section.id, item.id, question.id)}
                                            aria-label="Remover pergunta"
                                            disabled={totalQuestions <= 1}
                                          >
                                            <Trash2 size={16} />
                                          </button>
                                        </div>
                                      </div>

                                      <div className="admin-question-grid">
                                        <label className="full">
                                          <span>Enunciado</span>
                                          <textarea
                                            value={question.prompt}
                                            onChange={(event) =>
                                              updateQuestion(section.id, item.id, question.id, {
                                                prompt: event.target.value,
                                              })
                                            }
                                            placeholder="Digite a pergunta"
                                          ></textarea>
                                        </label>
                                        <label>
                                          <span>Tipo</span>
                                          <select
                                            value={question.type}
                                            onChange={(event) =>
                                              updateQuestion(section.id, item.id, question.id, {
                                                type: event.target.value as DraftQuestionType,
                                              })
                                            }
                                          >
                                            {availableQuestionTypes.map((option) => (
                                              <option key={option.code} value={option.code}>
                                                {option.label}
                                              </option>
                                            ))}
                                          </select>
                                        </label>
                                        <label>
                                          <span>Valor (pontos)</span>
                                          <input
                                            type="number"
                                            min={0}
                                            step={0.5}
                                            value={question.points}
                                            onChange={(event) =>
                                              updateQuestion(section.id, item.id, question.id, {
                                                points: event.target.value,
                                              })
                                            }
                                          />
                                        </label>
                                        <label className="checkbox-inline">
                                          <input
                                            type="checkbox"
                                            checked={question.required}
                                            onChange={(event) =>
                                              updateQuestion(section.id, item.id, question.id, {
                                                required: event.target.checked,
                                              })
                                            }
                                          />
                                          <span>Pergunta obrigatória</span>
                                        </label>
                                      </div>

                                      {question.type !== "ESSAY" ? (
                                        <div className="admin-option-list">
                                          {question.options.map((option, optionIndex) => (
                                            <div className="admin-option-row" key={option.id}>
                                              <label className="radio">
                                                <input
                                                  type="radio"
                                                  name={`correct-${question.id}`}
                                                  checked={option.isCorrect}
                                                  onChange={() => setCorrectOption(section.id, item.id, question.id, option.id)}
                                                />
                                                <span>Correta</span>
                                              </label>
                                              <input
                                                type="text"
                                                value={option.text}
                                                onChange={(event) =>
                                                  updateOption(section.id, item.id, question.id, option.id, {
                                                    text: event.target.value,
                                                  })
                                                }
                                                placeholder={`Alternativa ${optionIndex + 1}`}
                                                disabled={question.type === "TRUE_OR_FALSE"}
                                              />
                                              <div className="admin-option-actions">
                                                {question.type === "SINGLE_CHOICE" ? (
                                                  <>
                                                    <button
                                                      type="button"
                                                      className="icon-btn"
                                                      onClick={() => moveOption(section.id, item.id, question.id, option.id, -1)}
                                                      disabled={optionIndex === 0}
                                                      aria-label="Mover alternativa para cima"
                                                    >
                                                      <ArrowUp size={14} />
                                                    </button>
                                                    <button
                                                      type="button"
                                                      className="icon-btn"
                                                      onClick={() => moveOption(section.id, item.id, question.id, option.id, 1)}
                                                      disabled={optionIndex === question.options.length - 1}
                                                      aria-label="Mover alternativa para baixo"
                                                    >
                                                      <ArrowDown size={14} />
                                                    </button>
                                                    <button
                                                      type="button"
                                                      className="icon-btn danger"
                                                      onClick={() => removeOption(section.id, item.id, question.id, option.id)}
                                                      aria-label="Remover alternativa"
                                                      disabled={question.options.length <= 2}
                                                    >
                                                      <Trash2 size={14} />
                                                    </button>
                                                  </>
                                                ) : null}
                                              </div>
                                            </div>
                                          ))}
                                          {question.type === "SINGLE_CHOICE" ? (
                                            <button
                                              type="button"
                                              className="admin-btn admin-btn-ghost"
                                              onClick={() => addOption(section.id, item.id, question.id)}
                                            >
                                              <Plus size={14} /> Adicionar alternativa
                                            </button>
                                          ) : null}
                                        </div>
                                      ) : null}
                                    </div>
                                  );
                                })}

                                <button
                                  type="button"
                                  className="admin-btn admin-btn-secondary"
                                  onClick={() => addQuestion(section.id, item.id, "SINGLE_CHOICE")}
                                >
                                  <Plus size={16} /> Nova pergunta
                                </button>
                              </div>
                            </div>
                          ) : null}
                          <div className="admin-item-actions">
                            <button
                              type="button"
                              className="icon-btn"
                              onClick={() => moveItem(section.id, item.id, -1)}
                              disabled={itemIndex === 0}
                              aria-label="Mover item para cima"
                            >
                              <ArrowUp size={16} />
                            </button>
                            <button
                              type="button"
                              className="icon-btn"
                              onClick={() => moveItem(section.id, item.id, 1)}
                              disabled={itemIndex === section.items.length - 1}
                              aria-label="Mover item para baixo"
                            >
                              <ArrowDown size={16} />
                            </button>
                            <button
                              type="button"
                              className="icon-btn danger"
                              onClick={() => removeItem(section.id, item.id)}
                              aria-label="Remover item"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>

                    <button
                      type="button"
                      className="admin-btn admin-btn-secondary"
                      onClick={() => addItem(section.id)}
                    >
                      <Plus size={16} />
                      Adicionar item
                    </button>
                  </div>
                ))}

                {!sections.length ? (
                  <div className="admin-empty">Nenhuma seção cadastrada ainda.</div>
                ) : null}
              </div>
            </section>

            {saveError ? <div className="admin-alert is-error">{saveError}</div> : null}
            {saveSuccess ? <div className="admin-alert is-success">{saveSuccess}</div> : null}

            <div className="admin-builder-actions">
              <button
                type="button"
                className="admin-btn admin-btn-ghost"
                onClick={handleStartNewTrail}
                disabled={saving || loadingTrail}
              >
                Limpar
              </button>
              <button type="submit" className="admin-btn admin-btn-primary" disabled={saving}>
                {saving ? <Loader2 size={16} className="spin" /> : null}
                {isEditing ? "Atualizar rota" : "Salvar rota"}
              </button>
            </div>
          </form>
        )}
      </section>
    </Layout>
  );
}
