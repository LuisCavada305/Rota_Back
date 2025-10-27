import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { trackPageview } from "./analytics";

export default function AnalyticsRouterTracker() {
  const { pathname, search } = useLocation();
  useEffect(() => {
    trackPageview(pathname + search);
  }, [pathname, search]);
  return null;
}
