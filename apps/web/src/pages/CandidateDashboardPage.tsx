import { useCallback, useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ApiError, api, messageForError } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { Alert } from "../components/Alert";
import { EmptyState } from "../components/EmptyState";
import { employmentTypeLabel, formatDate } from "../components/JobCard";
import { LoadingState } from "../components/LoadingState";
import { PageTitle } from "../components/PageTitle";
import { Pagination } from "../components/Pagination";
import type { JobApplication, PaginatedResponse } from "../types/domain";

function flashFromState(state: unknown): string | null {
  if (
    typeof state === "object" &&
    state !== null &&
    "flash" in state &&
    typeof state.flash === "string"
  ) {
    return state.flash;
  }
  return null;
}

function statusLabel(status: string): string {
  return status
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function CandidateDashboardPage() {
  const { user } = useAuth();
  const location = useLocation();
  const [page, setPage] = useState(1);
  const [result, setResult] =
    useState<PaginatedResponse<JobApplication> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const loadApplications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await api.myApplications({ page, page_size: 8 }));
    } catch (requestError: unknown) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    void loadApplications();
  }, [loadApplications, reloadKey]);

  return (
    <>
      <PageTitle title="Your applications" />
      <header className="dashboard-header">
        <div className="container dashboard-header__inner">
          <div>
            <p className="eyebrow">Candidate dashboard</p>
            <h1>Your applications</h1>
            <p>
              Welcome back, {user?.full_name}. Keep every next step in view.
            </p>
          </div>
          <Link className="button" to="/jobs">
            Find another role
          </Link>
        </div>
      </header>

      <section
        className="container page"
        aria-labelledby="application-list-title"
      >
        {flashFromState(location.state) && (
          <Alert variant="success" title="Welcome to ShiftBridge">
            {flashFromState(location.state)}
          </Alert>
        )}
        <div className="results-heading">
          <div>
            <p className="eyebrow">Application history</p>
            <h2 id="application-list-title">
              {loading
                ? "Loading your activity"
                : `${result?.total ?? 0} submitted ${result?.total === 1 ? "application" : "applications"}`}
            </h2>
          </div>
        </div>

        {loading && <LoadingState label="Loading applications…" />}
        {!loading && error !== null && (
          <Alert
            variant="error"
            title="We could not load your applications"
            requestId={error instanceof ApiError ? error.requestId : undefined}
            onRetry={() => setReloadKey((key) => key + 1)}
          >
            {messageForError(error)}
          </Alert>
        )}
        {!loading && !error && result?.items.length === 0 && (
          <EmptyState
            title="No applications yet"
            action={
              <Link className="button" to="/jobs">
                Browse open roles
              </Link>
            }
          >
            When you apply for a role, its status and details will appear here.
          </EmptyState>
        )}
        {!loading && !error && result && result.items.length > 0 && (
          <>
            <div className="application-list">
              {result.items.map((application) => (
                <article className="application-row" key={application.id}>
                  <div>
                    <p className="application-row__company">
                      {application.job?.company_name ?? "ShiftBridge employer"}
                    </p>
                    <h3>
                      <Link to={`/jobs/${application.job_id}`}>
                        {application.job?.title ?? `Job #${application.job_id}`}
                      </Link>
                    </h3>
                    {application.job && (
                      <p className="job-meta">
                        <span>{application.job.location}</span>
                        <span>
                          {employmentTypeLabel(application.job.employment_type)}
                        </span>
                      </p>
                    )}
                  </div>
                  <div className="application-row__status">
                    <span className="status-badge">
                      {statusLabel(application.status)}
                    </span>
                    <small>Applied {formatDate(application.applied_at)}</small>
                  </div>
                </article>
              ))}
            </div>
            <Pagination
              page={result.page}
              totalPages={result.total_pages}
              onPageChange={setPage}
              label="Applications pagination"
            />
          </>
        )}
      </section>
    </>
  );
}
