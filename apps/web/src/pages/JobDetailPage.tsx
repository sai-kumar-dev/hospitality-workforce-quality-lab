import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { ApiError, api, messageForError } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { Alert } from "../components/Alert";
import { FormField } from "../components/FormField";
import { employmentTypeLabel, formatDate } from "../components/JobCard";
import { LoadingState } from "../components/LoadingState";
import { PageTitle } from "../components/PageTitle";
import type { Job } from "../types/domain";

const MAX_COVER_NOTE = 1000;

export function JobDetailPage() {
  const { jobId } = useParams();
  const parsedJobId = Number(jobId);
  const validJobId = Number.isInteger(parsedJobId) && parsedJobId > 0;
  const { user } = useAuth();
  const location = useLocation();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(validJobId);
  const [error, setError] = useState<unknown>(
    validJobId
      ? null
      : new ApiError({
          code: "INVALID_JOB_ID",
          title: "Job not found",
          status: 404,
          detail: "That job reference is not valid.",
        }),
  );
  const [reloadKey, setReloadKey] = useState(0);
  const [coverNote, setCoverNote] = useState("");
  const [coverNoteError, setCoverNoteError] = useState<string | undefined>();
  const [applicationError, setApplicationError] = useState<unknown>(null);
  const [applicationSent, setApplicationSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const loadJob = useCallback(
    async (signal: AbortSignal) => {
      if (!validJobId) return;
      setLoading(true);
      setError(null);
      try {
        const response = await api.job(parsedJobId, { signal });
        if (!signal.aborted) setJob(response);
      } catch (requestError: unknown) {
        if (!signal.aborted) setError(requestError);
      } finally {
        if (!signal.aborted) setLoading(false);
      }
    },
    [parsedJobId, validJobId],
  );

  useEffect(() => {
    const controller = new AbortController();
    void loadJob(controller.signal);
    return () => controller.abort();
  }, [loadJob, reloadKey]);

  async function submitApplication(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setApplicationError(null);
    const trimmedNote = coverNote.trim();
    if (!trimmedNote) {
      setCoverNoteError("Tell the employer briefly why this role fits you.");
      return;
    }
    if (trimmedNote.length > MAX_COVER_NOTE) {
      setCoverNoteError(`Use ${MAX_COVER_NOTE} characters or fewer.`);
      return;
    }
    setCoverNoteError(undefined);
    setSubmitting(true);
    try {
      await api.apply(parsedJobId, trimmedNote);
      setApplicationSent(true);
    } catch (requestError: unknown) {
      setApplicationError(requestError);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <section className="container page page--narrow">
        <PageTitle title="Loading job" />
        <LoadingState label="Loading job details…" />
      </section>
    );
  }

  if (error || !job) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <section className="container page page--narrow">
        <PageTitle title={notFound ? "Job not found" : "Job unavailable"} />
        <p className="eyebrow">
          {notFound ? "404 · Opportunity unavailable" : "Service issue"}
        </p>
        <h1>
          {notFound
            ? "This job could not be found"
            : "Job details are unavailable"}
        </h1>
        <Alert
          variant="error"
          title={
            notFound ? "The role may have been removed" : "Please try again"
          }
          requestId={error instanceof ApiError ? error.requestId : undefined}
          onRetry={notFound ? undefined : () => setReloadKey((key) => key + 1)}
        >
          {messageForError(error)}
        </Alert>
        <Link className="button button--secondary" to="/jobs">
          Back to all jobs
        </Link>
      </section>
    );
  }

  return (
    <>
      <PageTitle title={`${job.title} at ${job.company_name}`} />
      <header className="detail-hero">
        <div className="container">
          <Link className="back-link" to="/jobs">
            <span aria-hidden="true">←</span> Back to jobs
          </Link>
          <div className="detail-hero__heading">
            <span
              className="company-avatar company-avatar--large"
              aria-hidden="true"
            >
              {job.company_name.charAt(0).toUpperCase()}
            </span>
            <div>
              <p className="eyebrow">{job.company_name}</p>
              <h1>{job.title}</h1>
              <div className="job-meta">
                <span>{job.location}</span>
                <span>{employmentTypeLabel(job.employment_type)}</span>
                <span>Posted {formatDate(job.created_at)}</span>
              </div>
            </div>
            <span
              className={`status-badge ${job.active ? "" : "status-badge--muted"}`}
            >
              {job.active ? "Applications open" : "Applications closed"}
            </span>
          </div>
        </div>
      </header>

      <div className="container detail-layout page">
        <article className="detail-content">
          <section aria-labelledby="about-role">
            <p className="eyebrow">The opportunity</p>
            <h2 id="about-role">About this role</h2>
            <p className="pre-line">{job.description}</p>
          </section>
          <section aria-labelledby="skills">
            <h2 id="skills">Skills that will help you thrive</h2>
            {job.required_skills.length ? (
              <ul className="skill-list skill-list--large">
                {job.required_skills.map((skill) => (
                  <li key={skill}>{skill}</li>
                ))}
              </ul>
            ) : (
              <p>No specific skills were listed for this role.</p>
            )}
          </section>
          <section aria-labelledby="company">
            <h2 id="company">About {job.company_name}</h2>
            <p>
              This verified ShiftBridge employer is looking for thoughtful
              hospitality professionals to join its team in {job.location}.
            </p>
          </section>
        </article>

        <aside
          className="application-card"
          aria-labelledby="application-heading"
        >
          <p className="eyebrow">Your next step</p>
          <h2 id="application-heading">Apply for this role</h2>
          {!job.active && (
            <Alert title="Applications are closed">
              This employer is no longer accepting applications for this role.
            </Alert>
          )}
          {job.active && !user && (
            <>
              <p>
                Sign in with a candidate account to submit your application.
              </p>
              <Link
                className="button button--full"
                to="/login"
                state={{ from: `${location.pathname}${location.search}` }}
              >
                Sign in to apply
              </Link>
              <p className="application-card__secondary">
                New to ShiftBridge?{" "}
                <Link to="/register">Create an account</Link>
              </p>
            </>
          )}
          {job.active && user?.role === "employer" && (
            <Alert title="Employer account">
              Candidate applications cannot be submitted from an employer
              account.
            </Alert>
          )}
          {job.active && user?.role === "candidate" && applicationSent && (
            <Alert variant="success" title="Application submitted">
              Your application was sent to {job.company_name}.{" "}
              <Link to="/candidate">View your applications</Link>
            </Alert>
          )}
          {job.active && user?.role === "candidate" && !applicationSent && (
            <form
              noValidate
              onSubmit={(event) => void submitApplication(event)}
            >
              {applicationError !== null && (
                <Alert
                  variant="error"
                  title={
                    applicationError instanceof ApiError &&
                    applicationError.status === 409
                      ? "You already applied"
                      : "Application not submitted"
                  }
                  requestId={
                    applicationError instanceof ApiError
                      ? applicationError.requestId
                      : undefined
                  }
                >
                  {applicationError instanceof ApiError &&
                  applicationError.status === 409
                    ? "You have already applied for this role. You can review it in your applications."
                    : messageForError(applicationError)}
                </Alert>
              )}
              <FormField
                id="cover-note"
                label="Short cover note"
                hint={`Share your fit in ${MAX_COVER_NOTE} characters or fewer.`}
                error={coverNoteError}
              >
                <textarea
                  name="cover_note"
                  rows={7}
                  maxLength={MAX_COVER_NOTE}
                  value={coverNote}
                  onChange={(event) => setCoverNote(event.target.value)}
                />
              </FormField>
              <div className="character-count" aria-live="polite">
                {coverNote.length} / {MAX_COVER_NOTE}
              </div>
              <button
                className="button button--full"
                type="submit"
                disabled={submitting}
                aria-busy={submitting}
              >
                {submitting ? "Submitting…" : "Submit application"}
              </button>
            </form>
          )}
        </aside>
      </div>
    </>
  );
}
