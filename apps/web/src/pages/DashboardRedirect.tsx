import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { Alert } from "../components/Alert";
import { LoadingState } from "../components/LoadingState";

export function DashboardRedirect() {
  const { user, loading, sessionError, refresh, homeForRole } = useAuth();

  if (loading) {
    return (
      <div className="container page page--narrow">
        <LoadingState label="Opening your dashboard…" />
      </div>
    );
  }
  if (sessionError) {
    return (
      <div className="container page page--narrow">
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
  if (!user) return <Navigate replace to="/login" />;
  return <Navigate replace to={homeForRole(user.role)} />;
}
