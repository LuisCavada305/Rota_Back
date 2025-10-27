import { useEffect, useState } from "react";
import "../styles/Global.css";

export default function CookieError() {
  const [cookiesEnabled, setCookiesEnabled] = useState(true);

  useEffect(() => {
    // cria cookie de teste
    document.cookie = "test_cookie=1; path=/";
    const enabled = document.cookie.indexOf("test_cookie=") !== -1;

    if (!enabled) {
      setCookiesEnabled(false);
    } else {
      // limpa o cookie de teste
      document.cookie = "test_cookie=; Max-Age=0; path=/";
    }
  }, []);

  if (cookiesEnabled) return null;

  return (
    <div className="cookie-error" role="alert" aria-live="polite">
      Erro: seu navegador bloqueia ou não oferece suporte a cookies.  
      Você precisa ativar os cookies para usar o sistema.
    </div>
  );
}
