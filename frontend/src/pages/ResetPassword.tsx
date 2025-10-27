import "../styles/Login.css";
import Layout from "../components/Layout";
import Logo from "../images/rota-azul-medio.png";
import { NavLink, useSearchParams } from "react-router-dom";
import { useMemo, useState } from "react";
import { http } from "../lib/http";
import axios from "axios";
import CookieError from "../components/CookieErrorPopup";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = useMemo(() => params.get("token") ?? "", [params]);

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const EyeIcon = (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
      <circle cx="12" cy="12" r="3"></circle>
    </svg>
  );

  const EyeOffIcon = (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a21.77 21.77 0 0 1 5.06-7.94"></path>
      <path d="M1 1l22 22"></path>
      <path d="M9.53 9.53A3 3 0 0 0 12 15a3 3 0 0 0 2.47-5.47"></path>
    </svg>
  );

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!token) return;
    setErr(null);
    setSuccess(false);

    if (password.length < 8) {
      setErr("A nova senha deve ter pelo menos 8 caracteres.");
      return;
    }
    if (password !== confirmPassword) {
      setErr("As senhas não coincidem.");
      return;
    }

    setLoading(true);
    try {
      await http.post(
        "/auth/password/reset",
        { token, new_password: password },
        { suppressAuthModal: true }
      );
      setSuccess(true);
      setPassword("");
      setConfirmPassword("");
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status;
        const detail = (error.response?.data as any)?.detail;
        if (typeof detail === "string") {
          setErr(detail);
        } else if (Array.isArray(detail) && detail.length && typeof detail[0]?.msg === "string") {
          setErr(detail[0].msg);
        } else if (status === 401) {
          setErr("Link de redefinição inválido ou expirado. Solicite novamente.");
        } else {
          setErr("Não foi possível redefinir a senha. Tente novamente.");
        }
      } else {
        setErr("Erro inesperado. Tente novamente.");
      }
    } finally {
      setLoading(false);
    }
  };

  const tokenMissing = !token;

  return (
    <Layout>
      <div className="login-wrapper">
        <div className="login-card clean">
          <img className="login-logo" src={Logo} alt="ROTA" />
          <CookieError />

          <div className="form-head">
            <h2 className="head-left">Criar nova senha</h2>
            <NavLink className="head-right" to="/login">
              Voltar ao login
            </NavLink>
          </div>

          {tokenMissing ? (
            <div className="login-success" role="alert">
              O link de redefinição parece inválido. Solicite um novo link{" "}
              <NavLink to="/esqueci-minha-senha">clicando aqui</NavLink>.
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              <div className="form-field password-field">
                <input
                  type={showPassword ? "text" : "password"}
                  className="form-control with-icon icon-lock"
                  placeholder="Nova senha"
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                />
                <button
                  type="button"
                  className="password-visibility"
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
                >
                  {showPassword ? EyeOffIcon : EyeIcon}
                </button>
              </div>

              <div className="form-field password-field">
                <input
                  type={showConfirmation ? "text" : "password"}
                  className="form-control with-icon icon-lock"
                  placeholder="Confirme a nova senha"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={8}
                />
                <button
                  type="button"
                  className="password-visibility"
                  onClick={() => setShowConfirmation((prev) => !prev)}
                  aria-label={showConfirmation ? "Ocultar confirmação" : "Mostrar confirmação"}
                >
                  {showConfirmation ? EyeOffIcon : EyeIcon}
                </button>
              </div>

              <p className="form-helper-text">
                Use uma senha forte com pelo menos 8 caracteres. Você receberá um email de confirmação após a troca.
              </p>

              {err && (
                <div className="login-error" role="alert" aria-live="assertive">
                  {err}
                </div>
              )}

              {success && (
                <div className="login-success" role="status" aria-live="polite">
                  Senha atualizada com sucesso! Você já pode fazer login novamente.
                </div>
              )}

              <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                {loading ? "Atualizando..." : "Atualizar senha"}
              </button>

              <p className="terms">Termos e Serviços</p>
            </form>
          )}
        </div>
      </div>
    </Layout>
  );
}
