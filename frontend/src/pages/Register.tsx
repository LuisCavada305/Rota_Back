import "../styles/Login.css";
import Layout from "../components/Layout";
import Logo from "../images/rota-azul-medio.png";
import { NavLink } from "react-router-dom";
import { useState } from "react";
import { http } from "../lib/http";
import axios from "axios";
import CookieError from "../components/CookieErrorPopup";
import { Sex, sexOptions } from "../types/sex";
import { SkinColor, skinColorOptions } from "../types/skinColor";

export default function Register() {
        // SVGs para ícone de visibilidade
        const EyeIcon = (
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
        );
        const EyeOffIcon = (
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a21.77 21.77 0 0 1 5.06-7.94"></path><path d="M1 1l22 22"></path><path d="M9.53 9.53A3 3 0 0 0 12 15a3 3 0 0 0 2.47-5.47"></path></svg>
        );
    // Função para converter dd/mm/yyyy para yyyy-mm-dd
    function formatDateToYYYYMMDD(dateStr: string) {
        if (!dateStr) return "";
        const [day, month, year] = dateStr.split("/");
        if (!year || !month || !day) return dateStr;
        return `${year}-${month}-${day}`;
    }

    const [showPassword, setShowPassword] = useState(false);
    const [email, setEmail] = useState("");
    const [sex, setSex] = useState<Sex | "">("");
    const [color, setColor] = useState<SkinColor | "">("");
    const [password, setPassword] = useState("");
    const [name_for_certificate, setNameForCertificate] = useState("");
    const [social_name, setSocialName] = useState("");
    const [username, setUsername] = useState("");
    const [loading, setLoading] = useState(false);
    const [err, setErr] = useState<string | null>(null);
    const [birthday, setBirthday] = useState("");
    const [agree, setAgree] = useState(false);

    // Função de submit
    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setErr(null);
        setLoading(true);

        if (!sex || !color) {
            setErr("Selecione uma opção de gênero e de cor/raça.");
            setLoading(false);
            return;
        }

        const payload = {
            email: email.trim(),
            password,
            name_for_certificate,
            birthday: formatDateToYYYYMMDD(birthday),
            social_name,
            username,
            sex,
            color
        };

        try {
        const res = await http.post("/auth/register", payload, { suppressAuthModal: true });
        console.log("Registro e login OK:", res.data);
        window.location.href = "/"; // redireciona para a home
        } catch (error) {
        if (axios.isAxiosError(error)) {
            setErr((error.response?.data as any)?.detail || "Falha no registro");
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
                <h2 className="head-left">Crie sua conta</h2>
                <NavLink className="head-right" to="/login">
                    Já tenho uma conta
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
                                        type="text"
                                        className="form-control with-icon icon-user"
                                        placeholder="Nome de usuário"
                                        name="username"
                                        autoComplete="username"
                                        required
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                    />
                                </div>
        
                                <div className="form-field">
                                    <input
                                        type="text"
                                        className="form-control with-icon icon-user"
                                        placeholder="Nome social (Opcional)"
                                        autoComplete="name"
                                        value={social_name}
                                        onChange={(e) => setSocialName(e.target.value)}
                                    />
                                </div>

                                <div className="form-field select-field">

                                <select
                                    id="sex"
                                    name="sex"
                                    className="form-control"
                                    value={sex}
                                    required
                                    onChange={(e) => setSex(e.target.value as Sex)}
                                >
                                    <option value="" disabled>Gênero</option>
                                    {sexOptions.map(opt => (
                                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                                </div>

                                <div className="form-field select-field">
                                <select
                                    id="color"
                                    name="color"
                                    className="form-control"
                                    value={color}
                                    required
                                    onChange={(e) => setColor(e.target.value as SkinColor)}
                                >
                                    <option value="" disabled>Com qual cor/raça você se identifica?</option>
                                    {skinColorOptions.map(opt => (
                                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                                </div>

                                <div className="form-field">
                                    <input
                                        type="text"
                                        className="form-control with-icon icon-user"
                                        placeholder="Nome para os certificados"
                                        name="name_for_certificate"
                                        autoComplete="name"
                                        required
                                        value={name_for_certificate}
                                        onChange={(e) => setNameForCertificate(e.target.value)}
                                    />
                                </div>

                                <div className="form-field">
                                    <input
                                        type="text"
                                        className="form-control with-icon icon-lock"
                                        placeholder="Data de nascimento (dd/mm/yyyy)"
                                        name="birthday"
                                        autoComplete="bday"
                                        required
                                        value={birthday}
                                        onChange={(e) => {
                                            let v = e.target.value.replace(/[^\d\/]/g, "");
                                            // Adiciona barra automaticamente
                                            if (v.length === 2 && birthday.length === 1) v += "/";
                                            if (v.length === 5 && birthday.length === 4) v += "/";
                                            // Limita a 10 caracteres
                                            v = v.slice(0, 10);
                                            setBirthday(v);
                                        }}
                                        pattern="^(0[1-9]|[12][0-9]|3[01])\/(0[1-9]|1[0-2])\/\d{4}$"
                                    />
                                </div>

                               <div className="form-field password-field">
                                    <input
                                        type={showPassword ? "text" : "password"}
                                        className="form-control with-icon icon-lock"
                                        placeholder="Senha"
                                        name="pwd"
                                        autoComplete="current-password"
                                        required
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                    />

                                    <button
                                        type="button"
                                        className="password-visibility"
                                        onClick={() => setShowPassword((v) => !v)}
                                        aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
                                        title={showPassword ? "Ocultar senha" : "Mostrar senha"}
                                    >
                                        {showPassword ? EyeOffIcon : EyeIcon}
                                    </button>
                                </div>
                
                <div className="login-aux">
                    <label className="form-check">
                        <input
                        id="tutor-login-agmnt-1"
                        type="checkbox"
                        className="form-check-input"
                        name="agree"
                        checked={agree}
                        onChange={(e) => setAgree(e.target.checked)}
                        />
                        <span className="form-check-label">Concordo com o Termos e Serviços</span>
                    </label>
                </div>
            
                {err && <div className="login-error" role="alert" aria-live="polite">{err}</div>}

                <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                {loading ? "Processando..." : "Criar conta"}
                </button>


                <p className="terms">Termos e Serviços</p>
            </form>
            </div>
        </div>
        </Layout>
    );
}
