import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import "../styles/Header.css";
import LogoRota from "../images/LogoRotaHeader.png";
import { Home, GraduationCap, Users, MessageSquare, Search, Menu, X, ChevronDown } from "lucide-react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import Avatar from "../components/Avatar";
import { useAuth } from "../hooks/useAuth";
import type { Trilha } from "../types/Trilha";
import { http } from "../lib/http";

export default function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [allTrails, setAllTrails] = useState<Trilha[]>([]);
  const userMenuRef = useRef<HTMLDivElement | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const hasFetchedSearch = useRef(false);
  const { user, loading, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const isAdmin = user?.role === "Admin";

  const closeMobile = useCallback(() => setMobileOpen(false), []);
  const closeSearch = useCallback(() => {
    setSearchOpen(false);
    setSearchQuery("");
    setSearchError(null);
  }, []);

  // Fecha menu do usuário ao clicar fora
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!userMenuRef.current) return;
      if (!userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  // Fecha menus no escape + fecha drawer quando a rota muda
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeMobile();
        setUserMenuOpen(false);
        closeSearch();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [closeMobile, closeSearch]);

  useEffect(() => {
    setMobileOpen(false);
    setUserMenuOpen(false);
    closeSearch();
  }, [location.pathname, closeSearch, closeMobile]);

  // Evita scroll de fundo com drawer aberto
  useEffect(() => {
    if (mobileOpen) {
      document.body.classList.add("no-scroll");
    } else {
      document.body.classList.remove("no-scroll");
    }
    return () => {
      document.body.classList.remove("no-scroll");
    };
  }, [mobileOpen]);

  useEffect(() => {
    if (!searchOpen) return;
    setTimeout(() => searchInputRef.current?.focus(), 60);
    if (hasFetchedSearch.current) return;
    let cancelled = false;
    (async () => {
      try {
        setSearchLoading(true);
        const { data } = await http.get<{ trails?: Trilha[] }>("/trails/", {
          params: { page: 1, page_size: 100 },
        });
        if (cancelled) return;
        setAllTrails(data.trails ?? []);
        setSearchError(null);
        hasFetchedSearch.current = true;
      } catch (err: any) {
        if (cancelled) return;
        const detail =
          err?.response?.data?.detail ||
          err?.message ||
          "Não foi possível carregar as trilhas.";
        setSearchError(detail);
        hasFetchedSearch.current = false;
      } finally {
        if (!cancelled) {
          setSearchLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [searchOpen]);

  const normalizedQuery = searchQuery.trim().toLowerCase();
  const filteredTrails = useMemo(() => {
    if (!normalizedQuery) return allTrails;
    return allTrails.filter((trail) => {
      const name = trail.name?.toLowerCase() ?? "";
      const description = trail.description?.toLowerCase() ?? "";
      return name.includes(normalizedQuery) || description.includes(normalizedQuery);
    });
  }, [allTrails, normalizedQuery]);

  const visibleTrails = filteredTrails.slice(0, 8);
  const hasMoreResults = filteredTrails.length > visibleTrails.length;

  const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (filteredTrails.length) {
      handleNavigateToTrail(filteredTrails[0].id);
    }
  };

  const handleNavigateToTrail = (trailId: number) => {
    closeSearch();
    navigate(`/trail-details/${trailId}`);
  };

  return (
    <>
      <header id="masthead" className="site-header">
      <div className="site-header-container">
        {/* Logo */}
        <div id="site-logo" className="site-branding">
          <Link to="/" rel="home" onClick={closeMobile}>
            <img
              fetchPriority="high"
              width={180}
              src={LogoRota}
              className="bb-logo"
              alt="Logo Projeto Rota"
              decoding="async"
            />
          </Link>
        </div>

        {/* Botão hambúrguer – só mobile */}
        <button
          type="button"
          className="mobile-toggle"
          aria-label={mobileOpen ? "Fechar menu" : "Abrir menu"}
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen(v => !v)}
        >
          {mobileOpen ? <X size={22} /> : <Menu size={22} />}
        </button>

        {/* Navegação (desktop) */}
        <nav id="site-navigation" className="main-navigation desktop-nav">
          <ul className="primary-menu">
            <li className="menu-item">
              <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : undefined)}>
                <Home size={18} />
                <span>Home</span>
              </NavLink>
            </li>
            <li className="menu-item current-menu-item">
              <NavLink to="/trilhas" className={({ isActive }) => (isActive ? "active" : undefined)}>
                <GraduationCap size={18} />
                <span>Trilhas</span>
              </NavLink>
            </li>
            <li className="menu-item">
              <NavLink to="/membros" className={({ isActive }) => (isActive ? "active" : undefined)}>
                <Users size={18} />
                <span>Membros Enactus</span>
              </NavLink>
            </li>
            <li className="menu-item">
              <NavLink to="/foruns" className={({ isActive }) => (isActive ? "active" : undefined)}>
                <MessageSquare size={18} />
                <span>Fóruns</span>
              </NavLink>
            </li>
          </ul>
        </nav>

        {/* Ações (desktop) */}
        <div className="header-aside desktop-actions">
          <button
            type="button"
            className="header-search-link"
            aria-label="Procurar trilhas"
            onClick={() => setSearchOpen(true)}
          >
            <Search size={18} />
          </button>
          <span className="search-separator"></span>

          {/* Render condicional: se tem user → mostra menu do usuário. Senão → Entrar/Inscrever-se */}
          {!loading && user ? (
            <div className="user-menu" ref={userMenuRef}>
              <button
                className="user-button"
                aria-haspopup="menu"
                aria-expanded={userMenuOpen}
                onClick={() => setUserMenuOpen(v => !v)}
              >

                <span className="user-name">{user.username}</span>
                <Avatar name={user.username} src={user.profile_pic_url ?? null} />
                <ChevronDown size={16} className="chev" />
              </button>
              {userMenuOpen && (
                <div className="user-dropdown" role="menu">
                  <NavLink to="/painel" onClick={() => setUserMenuOpen(false)} role="menuitem">Painel</NavLink>
                  <NavLink to="/perfil" onClick={() => setUserMenuOpen(false)} role="menuitem">Perfil</NavLink>
                  {isAdmin ? (
                    <NavLink to="/admin" onClick={() => setUserMenuOpen(false)} role="menuitem">Admin</NavLink>
                  ) : null}
                  <button type="button" onClick={logout} className="logout-btn" role="menuitem">Sair</button>
                </div>
              )}
            </div>
          ) : (
            <div className="bb-header-buttons">
              <Link to="/login" className="signin-button">Entrar</Link>
              <Link to="/registro" className="signup">Inscrever-se</Link>
            </div>
          )}
        </div>
      </div>

      {/* Overlay do mobile */}
      <div className={`mobile-overlay ${mobileOpen ? "open" : ""}`} onClick={closeMobile}></div>

      {/* Menu lateral mobile */}
      <nav className={`mobile-nav-drawer ${mobileOpen ? "open" : ""}`} aria-hidden={!mobileOpen}>
        <button type="button" className="close-btn" onClick={closeMobile}>
          <X size={22} />
        </button>

        <ul className="mobile-menu">
          <li><NavLink to="/" end onClick={closeMobile} className={({isActive})=>isActive?'active':undefined}><Home size={18}/><span>Home</span></NavLink></li>
          <li><NavLink to="/trilhas" onClick={closeMobile} className={({isActive})=>isActive?'active':undefined}><GraduationCap size={18}/><span>Trilhas</span></NavLink></li>
          <li><NavLink to="/membros" onClick={closeMobile} className={({isActive})=>isActive?'active':undefined}><Users size={18}/><span>Membros Enactus</span></NavLink></li>
          <li><NavLink to="/foruns" onClick={closeMobile} className={({isActive})=>isActive?'active':undefined}><MessageSquare size={18}/><span>Fóruns</span></NavLink></li>
        </ul>

        {/* Ações no drawer (mobile): também condicional */}
        <div className="mobile-actions">
          {!loading && user ? (
            <div className="user-block">
              <div className="user-inline">
                <Avatar name={user.username} src={user.profile_pic_url} size={32}/>
                <div className="user-inline-name">{user.username}</div>
              </div>
              <NavLink to="/painel" onClick={closeMobile}>Painel</NavLink>
              <NavLink to="/perfil" onClick={closeMobile}>Perfil</NavLink>
              {isAdmin ? <NavLink to="/admin" onClick={closeMobile}>Admin</NavLink> : null}
              <button type="button" onClick={() => { logout(); closeMobile(); }} className="logout-btn">Sair</button>
            </div>
          ) : (
            <>
              <NavLink to="/login" className="signin-button" onClick={closeMobile}>Entrar</NavLink>
              <NavLink to="/registro" className="signup" onClick={closeMobile}>Inscrever-se</NavLink>
            </>
          )}
        </div>
      </nav>
      </header>
      {searchOpen ? (
        <>
          <div className="header-search-overlay" onClick={closeSearch} />
          <div className="header-search-dialog" role="dialog" aria-modal="true" aria-label="Pesquisar trilhas">
            <form className="header-search-form" onSubmit={handleSearchSubmit}>
              <Search size={18} />
              <input
                ref={searchInputRef}
                type="search"
                placeholder="Pesquisar trilhas pelo nome ou descrição…"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                aria-label="Pesquisar trilhas"
              />
              {searchQuery ? (
                <button
                  type="button"
                  className="header-search-clear"
                  onClick={() => setSearchQuery("")}
                  aria-label="Limpar busca"
                >
                  <X size={16} />
                </button>
              ) : null}
            </form>
            <div className="header-search-results">
              {searchLoading ? (
                <p className="search-hint">Carregando trilhas…</p>
              ) : searchError ? (
                <p className="search-error" role="alert">{searchError}</p>
              ) : visibleTrails.length ? (
                <>
                  <ul>
                    {visibleTrails.map((trail) => (
                      <li key={trail.id}>
                        <button type="button" onClick={() => handleNavigateToTrail(trail.id)}>
                          <span className="result-title">{trail.name}</span>
                          {trail.description ? (
                            <span className="result-description">{trail.description}</span>
                          ) : null}
                        </button>
                      </li>
                    ))}
                  </ul>
                  {hasMoreResults ? (
                    <p className="search-hint">Refine a busca para ver mais resultados.</p>
                  ) : null}
                  {!normalizedQuery ? (
                    <p className="search-hint muted">Digite para filtrar pelo nome da trilha.</p>
                  ) : null}
                </>
              ) : (
                <p className="search-hint">Nenhuma trilha encontrada.</p>
              )}
            </div>
          </div>
        </>
      ) : null}
    </>
  );
}
