import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, api, messageForError } from "../api/client";
import { Alert } from "../components/Alert";
import { EmptyState } from "../components/EmptyState";
import { formatDate } from "../components/JobCard";
import { LoadingState } from "../components/LoadingState";
import { PageTitle } from "../components/PageTitle";
import { Pagination } from "../components/Pagination";
import type {
  ApplicantApplication,
  Job,
  PaginatedResponse,
} from "../types/domain";

export function ApplicantsPage() {
  const { jobId } = useParams();
  const parsedJobId = Number(jobId);
  const validJobId = Number.isInteger(parsedJobId) && parsedJobId > 0;
  const [page, setPage] = useState(1);
  const [job, setJob] = useState<Job | null>(null);
  const [result, setResult] =
    useState<PaginatedResponse<ApplicantApplication> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const loadApplicants = useCallback(async () => {
    setLoading(true);
    setError(null);
    if (!validJobId) {
      setError(
        new ApiError({
          code: "INVALID_JOB_ID",
          title: "Job not found",
          status: 404,
          detail: "That job reference is not valid.",
        }),
      );
      setLoading(false);
      return;
    }
    try {
      const [jobResponse, applicantResponse] = await Promise.all([
        api.job(parsedJobId),
        api.applicants(parsedJobId, { page, page_size: 12 }),
      ]);
      setJob(jobResponse);
      setResult(applicantResponse);
    } catch (requestError: unknown) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }, [page, parsedJobId, validJobId]);

  useEffect(() => {
    void loadApplicants();
  }, [loadApplicants, reloadKey]);

  if (loading) {
    return (
      <section className="container page">
        <PageTitle title="Loading applicants" />
        <LoadingState label="Loading applicants…" />
      </section>
    );
  }

  if (error || !job || !result) {
    const forbidden = error instanceof ApiError && error.status === 403;
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <section className="container page page--narrow">
        <PageTitle
          title={
            forbidden
              ? "Access denied"
              : notFound
                ? "Job not found"
                : "Applicants unavailable"
          }
        />
        <p className="eyebrow">
          {forbidden
            ? "403 · Ownership required"
            : "Applicant list unavailable"}
        </p>
        <h1>
          {forbidden
            ? "Access denied"
            : notFound
              ? "This job could not be found"
              : "We could not load applicants"}
        </h1>
        <Alert
          variant="error"
          title={
            forbidden
              ? "This job belongs to another employer"
              : "The request could not be completed"
          }
          requestId={error instanceof ApiError ? error.requestId : undefined}
          onRetry={
            forbidden || notFound
              ? undefined
              : () => setReloadKey((key) => key + 1)
          }
        >
          {forbidden
            ? "For candidate privacy, only the employer who created a job can view its applicants."
            : messageForError(error)}
        </Alert>
        <Link className="button button--secondary" to="/employer">
          Back to employer hub
        </Link>
      </section>
    );
  }

  return (
    <>
      <PageTitle title={`Applicants for ${job.title}`} />
      <header className="dashboard-header dashboard-header--employer">
        <div className="container">
          <Link className="back-link back-link--light" to="/employer">
            <span aria-hidden="true">←</span> Back to employer hub
          </Link>
          <p className="eyebrow">{job.company_name}</p>
          <h1>Applicants for {job.title}</h1>
          <p>
            {result.total} {result.total === 1 ? "person is" : "people are"}{" "}
            ready for your review.
          </p>
        </div>
      </header>
      <section className="container page" aria-label="Applicant list">
        {result.items.length === 0 ? (
          <EmptyState title="No applicants yet">
            New applications for this role will appear here as they arrive.
          </EmptyState>
        ) : (
          <>
            <div className="applicant-list">
              {result.items.map((application) => (
                <article className="applicant-card" key={application.id}>
                  <header>
                    <span className="candidate-avatar" aria-hidden="true">
                      {application.candidate.full_name.charAt(0).toUpperCase()}
                    </span>
                    <div>
                      <h2>{application.candidate.full_name}</h2>
                      <a href={`mailto:${application.candidate.email}`}>
                        {application.candidate.email}
                      </a>
                    </div>
                    <span className="status-badge">{application.status}</span>
                  </header>
                  <section aria-labelledby={`note-${application.id}`}>
                    <h3 id={`note-${application.id}`}>Cover note</h3>
                    <p className="pre-line">{application.cover_note}</p>
                  </section>
                  <footer>Applied {formatDate(application.applied_at)}</footer>
                </article>
              ))}
            </div>
            <Pagination
              page={result.page}
              totalPages={result.total_pages}
              onPageChange={setPage}
              label="Applicants pagination"
            />
          </>
        )}
      </section>
    </>
  );
}
