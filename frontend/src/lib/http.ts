// src/lib/http.ts
import axios, { AxiosError, AxiosHeaders } from "axios";
import type { InternalAxiosRequestConfig, AxiosRequestHeaders } from "axios";

declare module "axios" {
  // permite marcar chamadas que NÃO devem abrir o modal
  export interface InternalAxiosRequestConfig {
    suppressAuthModal?: boolean;
  }
}

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  withCredentials: true,
});

http.defaults.xsrfCookieName = "rota_csrftoken";
http.defaults.xsrfHeaderName = "X-CSRF-Token";

const CSRF_STORAGE_KEY = "rota.csrfToken";

function storeCsrfToken(token: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (!token) {
      window.sessionStorage.removeItem(CSRF_STORAGE_KEY);
      delete http.defaults.headers.common["X-CSRF-Token"];
      delete http.defaults.headers.common["X-CSRFToken"];
      return;
    }
    window.sessionStorage.setItem(CSRF_STORAGE_KEY, token);
    http.defaults.headers.common["X-CSRF-Token"] = token;
    http.defaults.headers.common["X-CSRFToken"] = token;
  } catch (err) {
    console.warn("Não foi possível salvar o CSRF token na sessionStorage", err);
  }
}

function readStoredCsrfToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(CSRF_STORAGE_KEY);
  } catch (err) {
    console.warn("Não foi possível ler o CSRF token da sessionStorage", err);
    return null;
  }
}

const bootstrapToken = readStoredCsrfToken() || getCookie("rota_csrftoken");
if (bootstrapToken) {
  storeCsrfToken(bootstrapToken);
}

function getCookie(name: string): string | null {
  const cookies = document.cookie ? document.cookie.split(";") : [];
  for (const raw of cookies) {
    const [key, ...rest] = raw.trim().split("=");
    if (key === name) {
      return decodeURIComponent(rest.join("="));
    }
  }
  return null;
}

function readHeader(headers: unknown, names: string[]): string | undefined {
  if (!headers) return undefined;
  const maybeGet = headers as { get?: (h: string) => string | undefined };
  if (typeof maybeGet.get === "function") {
    for (const name of names) {
      const value = maybeGet.get(name);
      if (value) return value;
    }
  }
  const record = headers as Record<string, string | undefined>;
  for (const name of names) {
    const lower = name.toLowerCase();
    const value = record?.[name] ?? record?.[lower];
    if (value) return value;
  }
  return undefined;
}

http.interceptors.request.use((config) => {
  const method = (config.method ?? "get").toLowerCase();
  if (["post", "put", "patch", "delete"].includes(method)) {
    const token = getCookie("rota_csrftoken") || readStoredCsrfToken();
    if (token) {
      if (config.headers instanceof AxiosHeaders) {
        config.headers.set("X-CSRF-Token", token);
        config.headers.set("X-CSRFToken", token);
      } else {
        const headers = AxiosHeaders.from(config.headers ?? {} as AxiosRequestHeaders);
        headers.set("X-CSRF-Token", token);
        headers.set("X-CSRFToken", token);
        config.headers = headers;
      }
    }
  }
  return config;
});

http.interceptors.response.use(
  (res) => {
    const tokenFromHeader = readHeader(res.headers, ["X-CSRF-Token", "X-CSRFToken"]);
    if (tokenFromHeader) {
      storeCsrfToken(tokenFromHeader);
    }
    return res;
  },
  (err: AxiosError) => {
    const status = err.response?.status ?? 0;
    const cfg = err.config as InternalAxiosRequestConfig | undefined;
    const path = cfg?.url ?? "";

    const isUnauthorizedLike = status === 409 || status === 401 || status === 403;
    const isAuthFlowRequest =
      typeof path === "string" &&
      (path.includes("/auth/login") || path.includes("/auth/register"));

    if (isUnauthorizedLike && !cfg?.suppressAuthModal && !isAuthFlowRequest) {
      window.dispatchEvent(
        new CustomEvent("auth:unauthorized", {
          detail: { status, path },
        })
      );
    }
    const tokenFromHeader = readHeader(err.response?.headers, ["X-CSRF-Token", "X-CSRFToken"]);
    if (tokenFromHeader) {
      storeCsrfToken(tokenFromHeader);
    } else if (status === 419 || status === 403) {
      // tokens podem ter expirado ou sido limpos
      storeCsrfToken(null);
    }
    // sempre propaga o erro para quem chamou poder tratar se quiser
    return Promise.reject(err);
  }
);
