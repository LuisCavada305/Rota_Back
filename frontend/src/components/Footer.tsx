// src/components/Footer.tsx
import { NavLink } from "react-router-dom";
import { Instagram, Youtube, Linkedin } from "lucide-react";
import "../styles/Footer.css";
export default function Footer() {
  return (
    <footer className="footer-bottom bb-footer style-1">
      <div className="container flex">
        <div className="footer-bottom-left">
          <div className="footer-copyright-wrap">
            <div className="copyright">© 2025 - Enactus Mackenzie</div>

            <ul id="menu-rodape" className="footer-menu secondary">
              <li className="menu-item">
                {/* se /blog não existir no SPA, troque por <a href="https://projetorota.com.br/blog/"> */}
                <NavLink
                  to="/blog"
                  className={({ isActive }) => (isActive ? "is-active" : undefined)}
                >
                  <span className="link-text">Postagens</span>
                </NavLink>
              </li>

              <li className="menu-item">
                <NavLink
                  to="/trilhas"
                  className={({ isActive }) => (isActive ? "is-active" : undefined)}
                >
                  <span className="link-text">Trilhas</span>
                </NavLink>
              </li>
            </ul>
          </div>
        </div>

        <div className="footer-bottom-right push-right">
          <ul className="footer-socials">
            <li>
              <a
                href="https://www.instagram.com/enactusmackenzie/"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Instagram Enactus Mackenzie"
                data-balloon-pos="up"
                data-balloon="instagram"
              >
                <Instagram width={18} height={18} />
              </a>
            </li>
            <li>
              <a
                href="https://www.youtube.com/@enactusmackenzie9248"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="YouTube Enactus Mackenzie"
                data-balloon-pos="up"
                data-balloon="youtube"
              >
                <Youtube width={18} height={18} />
              </a>
            </li>
            <li>
              <a
                href="https://br.linkedin.com/company/enactus-mackenzie"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="LinkedIn Enactus Mackenzie"
                data-balloon-pos="up"
                data-balloon="linkedin"
              >
                <Linkedin width={18} height={18} />
              </a>
            </li>
          </ul>
        </div>
      </div>
    </footer>
  );
}
