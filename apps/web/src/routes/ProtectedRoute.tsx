import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { Alert } from "../components/Alert";
import { LoadingState } from "../components/LoadingState";
import { PageTitle } from "../components/PageTitle";
import type { Role } from "../types/domain";

export function ProtectedRoute({ role }: { role: Role }) {
  const { user, loading, sessionError, refresh } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="container page page--narrow">
        <LoadingState label="Checking your session…" />
      </div>
    );
  }

  if (sessionError && !user) {
    return (
      <div className="container page page--narrow">
        <PageTitle title="Session unavailable" />
        <Alert
          variant="error"
          title="We could not verify your session"
          onRetry={() => void refresh()}
        >
          {sessionError}
        </Alert>
      </div>
    );
  }

  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: `${location.pathname}${location.search}` }}
      />
    );
  }

  if (user.role !== role) {
    return (
      <section className="container page page--narrow">
        <PageTitle title="Access denied" />
        <p className="eyebrow">403 · Role restricted</p>
        <h1>Access denied</h1>
        <p className="lead">
          This area is available only to {role}s. Your account is signed in as a{" "}
          {user.role}.
        </p>
        <a
          className="button"
          href={user.role === "candidate" ? "/candidate" : "/employer"}
        >
          Go to your dashboard
        </a>
      </section>
    );
  }

  return <Outlet />;
}
