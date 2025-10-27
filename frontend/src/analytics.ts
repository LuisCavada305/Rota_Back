export function trackPageview(path: string) {
  // @ts-ignore
  window.gtag?.("event", "page_view", { page_path: path });
}

export function trackEvent(name: string, params?: Record<string, any>) {
  // @ts-ignore
  window.gtag?.("event", name, params);
}
