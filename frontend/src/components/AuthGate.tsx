import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/AuthGate.css";

type Detail = { status: number; path: string };

export default function AuthGate() {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<Detail | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const handler = (e: Event) => {
      const ce = e as CustomEvent<Detail>;
      setDetail(ce.detail);
      setOpen(true);
    };
    window.addEventListener("auth:unauthorized", handler as EventListener);
    return () => window.removeEventListener("auth:unauthorized", handler as EventListener);
  }, []);

  const goLogin = () => {
    setOpen(false);
    navigate("/login");
  };

  if (!open) return null;

  return (
    <div className="auth-overlay">
      <div className="auth-modal">
        <h2>Sessão expirada</h2>
        <p>
          Você não está logado ou sua sessão expirou.
          {detail ? ` (código ${detail.status})` : null}
        </p>
        <div className="auth-actions">
          <button onClick={() => setOpen(false)} className="auth-btn close">
            Fechar
          </button>
          <button onClick={goLogin} className="auth-btn login">
            Ir para login
          </button>
        </div>
      </div>
    </div>
  );
}
