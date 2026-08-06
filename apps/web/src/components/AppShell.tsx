import { useEffect, useState } from "react";
import {
  Link,
  NavLink,
  Outlet,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { messageForError } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { Alert } from "./Alert";

function navClass({ isActive }: { isActive: boolean }): string {
  return isActive ? "nav-link nav-link--active" : "nav-link";
}

export function AppShell() {
  const { user, loading, logout, homeForRole } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  async function handleLogout() {
    setLogoutError(null);
    try {
      await logout();
      navigate("/", { replace: true });
    } catch (error: unknown) {
      setLogoutError(messageForError(error));
      navigate("/", { replace: true });
    }
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <header className="site-header">
        <div className="container nav-bar">
          <Link className="brand" to="/" aria-label="ShiftBridge home">
            <span className="brand__mark" aria-hidden="true">
              SB
            </span>
            <span>
              <strong>ShiftBridge</strong>
              <small>Hospitality careers</small>
            </span>
          </Link>

          <button
            type="button"
            className="menu-button"
            aria-expanded={menuOpen}
            aria-controls="primary-navigation"
            onClick={() => setMenuOpen((current) => !current)}
          >
            <span className="menu-button__lines" aria-hidden="true" />
            {menuOpen ? "Close navigation" : "Open navigation"}
          </button>

          <nav
            id="primary-navigation"
            className={`primary-nav${menuOpen ? " primary-nav--open" : ""}`}
            aria-label="Primary navigation"
          >
            <NavLink className={navClass} to="/jobs">
              Find jobs
            </NavLink>
            {!loading && user && (
              <NavLink className={navClass} to={homeForRole(user.role)}>
                {user.role === "candidate" ? "My applications" : "Employer hub"}
              </NavLink>
            )}
            {!loading && !user && (
              <>
                <NavLink className={navClass} to="/login">
                  Sign in
                </NavLink>
                <Link className="button button--small" to="/register">
                  Join as candidate
                </Link>
              </>
            )}
            {!loading && user && (
              <div className="nav-account">
                <span className="nav-account__name">
                  <span aria-hidden="true">{user.full_name.charAt(0)}</span>
                  <span className="sr-only">Signed in as </span>
                  {user.full_name}
                </span>
                <button
                  className="button button--small button--ghost"
                  type="button"
                  onClick={() => void handleLogout()}
                >
                  Sign out
                </button>
              </div>
            )}
          </nav>
        </div>
      </header>

      {logoutError && (
        <div className="container shell-alert">
          <Alert variant="error" title="Signed out locally">
            Your browser session was cleared, but the server could not be
            reached.
            {` ${logoutError}`}
          </Alert>
        </div>
      )}

      <main id="main-content" tabIndex={-1}>
        <Outlet />
      </main>

      <footer className="site-footer">
        <div className="container site-footer__inner">
          <div>
            <strong>ShiftBridge</strong>
            <p>Where hospitality talent and trusted teams meet.</p>
          </div>
          <nav aria-label="Footer navigation">
            <Link to="/jobs">Browse jobs</Link>
            <Link to="/login">Employer sign in</Link>
          </nav>
          <small>
            © {new Date().getFullYear()} ShiftBridge demo marketplace
          </small>
        </div>
      </footer>
    </div>
  );
}
