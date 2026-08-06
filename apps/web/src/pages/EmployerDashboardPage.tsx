import { useCallback, useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ApiError, api, messageForError } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { Alert } from "../components/Alert";
import { EmptyState } from "../components/EmptyState";
import { JobCard } from "../components/JobCard";
import { LoadingState } from "../components/LoadingState";
import { PageTitle } from "../components/PageTitle";
import { Pagination } from "../components/Pagination";
import type { Job, PaginatedResponse } from "../types/domain";

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

export function EmployerDashboardPage() {
  const { user } = useAuth();
  const location = useLocation();
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<PaginatedResponse<Job> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await api.employerJobs({ page, page_size: 8 }));
    } catch (requestError: unknown) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs, reloadKey]);

  return (
    <>
      <PageTitle title="Employer hub" />
      <header className="dashboard-header dashboard-header--employer">
        <div className="container dashboard-header__inner">
          <div>
            <p className="eyebrow">Employer hub</p>
            <h1>Your job posts</h1>
            <p>
              Manage your open roles and review the people ready to contribute.
            </p>
          </div>
          <Link className="button button--light" to="/employer/jobs/new">
            Create a job
          </Link>
        </div>
      </header>

      <section className="container page" aria-labelledby="employer-job-list">
        {flashFromState(location.state) && (
          <Alert variant="success" title="Job published">
            {flashFromState(location.state)}
          </Alert>
        )}
        <div className="results-heading">
          <div>
            <p className="eyebrow">Your hiring activity</p>
            <h2 id="employer-job-list">
              {loading
                ? "Loading your job posts"
                : `${result?.total ?? 0} ${result?.total === 1 ? "job post" : "job posts"}`}
            </h2>
          </div>
          <p className="muted">Signed in as {user?.email}</p>
        </div>

        {loading && <LoadingState label="Loading your job posts…" />}
        {!loading && error !== null && (
          <Alert
            variant="error"
            title="We could not load your job posts"
            requestId={error instanceof ApiError ? error.requestId : undefined}
            onRetry={() => setReloadKey((key) => key + 1)}
          >
            {messageForError(error)}
          </Alert>
        )}
        {!loading && !error && result?.items.length === 0 && (
          <EmptyState
            title="Publish your first role"
            action={
              <Link className="button" to="/employer/jobs/new">
                Create a job
              </Link>
            }
          >
            Your active and closed job posts will be managed from this space.
          </EmptyState>
        )}
        {!loading && !error && result && result.items.length > 0 && (
          <>
            <div className="job-list">
              {result.items.map((job) => (
                <JobCard employerView job={job} key={job.id} />
              ))}
            </div>
            <Pagination
              page={result.page}
              totalPages={result.total_pages}
              onPageChange={setPage}
              label="Employer jobs pagination"
            />
          </>
        )}
      </section>
    </>
  );
}
