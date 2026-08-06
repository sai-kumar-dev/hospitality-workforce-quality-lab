import { Link } from "react-router-dom";
import type { Job } from "../types/domain";

export function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function employmentTypeLabel(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function JobCard({
  job,
  employerView = false,
}: {
  job: Job;
  employerView?: boolean;
}) {
  return (
    <article className="job-card">
      <div className="job-card__topline">
        <span className="company-avatar" aria-hidden="true">
          {job.company_name.charAt(0).toUpperCase()}
        </span>
        <div>
          <p className="job-card__company">{job.company_name}</p>
          <h2>
            <Link to={`/jobs/${job.id}`}>{job.title}</Link>
          </h2>
        </div>
        <span
          className={`status-badge ${job.active ? "" : "status-badge--muted"}`}
        >
          {job.active ? "Open" : "Closed"}
        </span>
      </div>
      <div className="job-meta" aria-label="Job details">
        <span>{job.location}</span>
        <span>{employmentTypeLabel(job.employment_type)}</span>
        <span>Posted {formatDate(job.created_at)}</span>
      </div>
      <p className="job-card__description">{job.description}</p>
      <div className="skill-list" aria-label="Required skills">
        {job.required_skills.slice(0, 4).map((skill) => (
          <span key={skill}>{skill}</span>
        ))}
      </div>
      <div className="job-card__actions">
        <Link
          className="text-link"
          to={`/jobs/${job.id}`}
          aria-label={`View ${job.title} at ${job.company_name}`}
        >
          View role <span aria-hidden="true">→</span>
        </Link>
        {employerView && (
          <Link
            className="button button--small button--secondary"
            to={`/employer/jobs/${job.id}/applicants`}
          >
            View applicants
          </Link>
        )}
      </div>
    </article>
  );
}
