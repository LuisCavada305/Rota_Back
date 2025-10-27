import "../styles/Login.css";
import Layout from "../components/Layout";
import Logo from "../images/rota-azul-medio.png";
import { NavLink } from "react-router-dom";
import { useState } from "react";
import { http } from "../lib/http";
import axios from "axios";
import CookieError from "../components/CookieErrorPopup";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErr(null);
    setSent(false);
    setLoading(true);

    try {
      await http.post(
        "/auth/password/forgot",
        { email: email.trim() },
        { suppressAuthModal: true }
      );
      setSent(true);
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status;
        if (status === 429) {
          const retryAfter = error.response?.headers?.["retry-after"];
          const suffix = retryAfter ? ` Aguarde ${retryAfter} segundos.` : "";
          setErr(`Muitas tentativas. Tente novamente em instantes.${suffix}`);
        } else if (status === 404) {
          setSent(true);
          setErr(null);
        } else {
          const detail = (error.response?.data as any)?.detail;
          if (typeof detail === "string") {
            if (detail.toLowerCase().includes("não cadastrado") || detail.toLowerCase().includes("nao cadastrado")) {
              setSent(true);
              setErr(null);
            } else {
              setErr(detail);
            }
          } else if (Array.isArray(detail) && detail.length && typeof detail[0]?.msg === "string") {
            setErr(detail[0].msg);
          } else {
            setErr("Não foi possível enviar o email de redefinição.");
          }
        }
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
            <h2 className="head-left">Redefinir senha</h2>
            <NavLink className="head-right" to="/login">
              Voltar para o login
            </NavLink>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-field">
              <input
                type="email"
                className="form-control with-icon icon-user"
                placeholder="Endereço de email"
                value={email}
                required
                autoComplete="email"
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <p className="form-helper-text">
              Informe o email da sua conta. Se ele existir, enviaremos um link para redefinir a senha.
            </p>

            {err && (
              <div className="login-error" role="alert" aria-live="assertive">
                {err}
              </div>
            )}

            {sent && !err && (
              <div className="login-success" role="status" aria-live="polite">
                Se encontrarmos uma conta com este email, você receberá um link para criar uma nova senha.
              </div>
            )}

            <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
              {loading ? "Enviando..." : "Enviar link"}
            </button>

            <p className="terms">Termos e Serviços</p>
          </form>
        </div>
      </div>
    </Layout>
  );
}
