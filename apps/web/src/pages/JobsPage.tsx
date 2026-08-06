import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { ApiError, api, messageForError } from "../api/client";
import { Alert } from "../components/Alert";
import { EmptyState } from "../components/EmptyState";
import { FormField } from "../components/FormField";
import { JobCard } from "../components/JobCard";
import { LoadingState } from "../components/LoadingState";
import { PageTitle } from "../components/PageTitle";
import { Pagination } from "../components/Pagination";
import type { Job, PaginatedResponse } from "../types/domain";

const PAGE_SIZE = 8;

export function JobsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const keywordParam = searchParams.get("keyword") ?? "";
  const locationParam = searchParams.get("location") ?? "";
  const parsedPage = Number(searchParams.get("page") ?? "1");
  const page = Number.isInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1;

  const [keyword, setKeyword] = useState(keywordParam);
  const [location, setLocation] = useState(locationParam);
  const [result, setResult] = useState<PaginatedResponse<Job> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const loadJobs = useCallback(
    async (signal: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.jobs({
          keyword: keywordParam,
          location: locationParam,
          page,
          page_size: PAGE_SIZE,
        });
        if (!signal.aborted) setResult(response);
      } catch (requestError: unknown) {
        if (!signal.aborted) setError(requestError);
      } finally {
        if (!signal.aborted) setLoading(false);
      }
    },
    [keywordParam, locationParam, page],
  );

  useEffect(() => {
    const controller = new AbortController();
    void loadJobs(controller.signal);
    return () => controller.abort();
  }, [loadJobs, reloadKey]);

  useEffect(() => {
    setKeyword(keywordParam);
    setLocation(locationParam);
  }, [keywordParam, locationParam]);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = new URLSearchParams();
    if (keyword.trim()) next.set("keyword", keyword.trim());
    if (location.trim()) next.set("location", location.trim());
    setSearchParams(next);
  }

  function clearFilters() {
    setKeyword("");
    setLocation("");
    setSearchParams({});
  }

  function changePage(nextPage: number) {
    const next = new URLSearchParams(searchParams);
    next.set("page", String(nextPage));
    setSearchParams(next);
    document.getElementById("job-results")?.focus();
  }

  return (
    <>
      <PageTitle title="Find hospitality jobs" />
      <header className="page-hero page-hero--jobs">
        <div className="container">
          <p className="eyebrow">Roles with room to grow</p>
          <h1>Find your next hospitality role</h1>
          <p>
            Explore opportunities from trusted hotels and restaurants, then
            apply in a few focused steps.
          </p>
          <form className="search-panel" role="search" onSubmit={applyFilters}>
            <FormField id="job-keyword" label="Keyword">
              <input
                type="search"
                name="keyword"
                placeholder="e.g. chef, front desk"
                value={keyword}
                onChange={(event) => setKeyword(event.target.value)}
              />
            </FormField>
            <FormField id="job-location" label="Location">
              <input
                type="search"
                name="location"
                placeholder="e.g. Dublin"
                value={location}
                onChange={(event) => setLocation(event.target.value)}
              />
            </FormField>
            <button className="button" type="submit">
              Search jobs
            </button>
          </form>
        </div>
      </header>

      <section
        className="container page jobs-content"
        aria-labelledby="job-results"
      >
        <div className="results-heading">
          <div>
            <p className="eyebrow">Current opportunities</p>
            <h2 id="job-results" tabIndex={-1}>
              {loading
                ? "Searching roles"
                : `${result?.total ?? 0} ${result?.total === 1 ? "role" : "roles"} found`}
            </h2>
          </div>
          {(keywordParam || locationParam) && (
            <button className="button button--ghost" onClick={clearFilters}>
              Clear filters
            </button>
          )}
        </div>

        {loading && <LoadingState label="Loading jobs…" />}
        {!loading && error !== null && (
          <Alert
            variant="error"
            title="We could not load jobs"
            requestId={error instanceof ApiError ? error.requestId : undefined}
            onRetry={() => setReloadKey((key) => key + 1)}
          >
            {messageForError(error)}
          </Alert>
        )}
        {!loading && !error && result?.items.length === 0 && (
          <EmptyState
            title="No roles match those filters"
            action={
              <button
                className="button button--secondary"
                onClick={clearFilters}
              >
                View all jobs
              </button>
            }
          >
            Try a broader keyword or another location.
          </EmptyState>
        )}
        {!loading && !error && result && result.items.length > 0 && (
          <>
            <div className="job-list">
              {result.items.map((job) => (
                <JobCard job={job} key={job.id} />
              ))}
            </div>
            <Pagination
              page={result.page}
              totalPages={result.total_pages}
              onPageChange={changePage}
              label="Job results pagination"
            />
          </>
        )}
      </section>
    </>
  );
}
