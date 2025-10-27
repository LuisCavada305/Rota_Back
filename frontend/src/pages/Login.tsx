import "../styles/Login.css";
import Layout from "../components/Layout";
import Logo from "../images/rota-azul-medio.png";
import { NavLink } from "react-router-dom";
import { useState } from "react";
import { http } from "../lib/http";
import axios from "axios";
import CookieError
 from "../components/CookieErrorPopup";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Função de submit
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErr(null);
    setLoading(true);

    const payload = { email: email.trim(), password, remember };

    try {
      const res = await http.post("/auth/login", payload, { suppressAuthModal: true });
      console.log("Login OK:", res.data);
      window.location.href = "/"; // redireciona para a home
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status;
        let message: string | null = null;
        const dataDetail = (error.response?.data as any)?.detail;

        if (typeof dataDetail === "string" && dataDetail.trim()) {
          message = dataDetail;
        } else if (Array.isArray(dataDetail) && dataDetail.length) {
          const first = dataDetail[0];
          if (typeof first?.msg === "string") {
            message = first.msg;
          }
        }

        if (status === 401) {
          message = message ?? "Credenciais inválidas. Verifique seu email e senha.";
        } else if (status === 429) {
          const retryAfter = error.response?.headers?.["retry-after"];
          const suffix = retryAfter ? ` Aguarde ${retryAfter} segundos.` : "";
          message = `Muitas tentativas. Tente novamente em instantes.${suffix}`;
        }

        setErr(message ?? `Falha no login${status ? ` (código ${status})` : ""}.`);
      } else {
        setErr("Erro inesperado. Tente novamente.");
      }
    } finally {
      setLoading(false);
    }
};

  return (
    <Layout>
      <div className="login-wrapper">
        <div className="login-card clean">
          <img className="login-logo" src={Logo} alt="ROTA" />

          <CookieError />
          <div className="form-head">
            <h2 className="head-left">Entrar</h2>
            <NavLink className="head-right" to="/registro">
              Crie a sua conta aqui
            </NavLink>
          </div>

          <form id="tutor-login-form" method="post" onSubmit={handleSubmit}>
            <div className="form-field">
              <input
                type="email"
                className="form-control with-icon icon-user"
                placeholder="Endereço de email"
                name="log"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div className="form-field">
              <input 
                type="password"
                className="form-control with-icon icon-lock"
                placeholder="Senha"
                name="pwd"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <div className="login-aux">
              <label className="form-check">
                <input
                  id="tutor-login-agmnt-1"
                  type="checkbox"
                  className="form-check-input"
                  name="remember"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                />
                <span className="form-check-label">Lembrar de mim</span>
              </label>

              <NavLink
                to="/esqueci-minha-senha"
                className="aux-link"
              >
                Esqueceu sua senha?
              </NavLink>
            </div>
           
            {err && <div className="login-error" role="alert" aria-live="polite">{err}</div>}

            <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
              {loading ? "Entrando..." : "Acessar"}
            </button>


            <p className="terms">Termos e Serviços</p>
          </form>
        </div>
      </div>
    </Layout>
  );
}
