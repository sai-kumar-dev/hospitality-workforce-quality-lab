import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, api, fieldErrorsFor, messageForError } from "../api/client";
import { Alert } from "../components/Alert";
import { FormField } from "../components/FormField";
import { PageTitle } from "../components/PageTitle";

interface JobFormErrors {
  title?: string;
  company_name?: string;
  location?: string;
  employment_type?: string;
  description?: string;
  required_skills?: string;
}

export function CreateJobPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [location, setLocation] = useState("");
  const [employmentType, setEmploymentType] = useState("");
  const [description, setDescription] = useState("");
  const [skills, setSkills] = useState("");
  const [active, setActive] = useState(true);
  const [errors, setErrors] = useState<JobFormErrors>({});
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  function validate(): JobFormErrors {
    const nextErrors: JobFormErrors = {};
    if (title.trim().length < 3)
      nextErrors.title = "Enter a job title of at least 3 characters.";
    if (companyName.trim().length < 2)
      nextErrors.company_name = "Enter the company name.";
    if (location.trim().length < 2)
      nextErrors.location = "Enter the job location.";
    if (!employmentType)
      nextErrors.employment_type = "Choose an employment type.";
    if (description.trim().length < 20)
      nextErrors.description =
        "Describe the opportunity in at least 20 characters.";
    if (!skills.split(",").some((skill) => skill.trim()))
      nextErrors.required_skills = "Add at least one required skill.";
    return nextErrors;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors = validate();
    setErrors(nextErrors);
    setSubmitError(null);
    if (Object.keys(nextErrors).length) return;

    setSubmitting(true);
    try {
      const job = await api.createJob({
        title: title.trim(),
        company_name: companyName.trim(),
        location: location.trim(),
        employment_type: employmentType,
        description: description.trim(),
        required_skills: skills
          .split(",")
          .map((skill) => skill.trim())
          .filter(Boolean),
        active,
      });
      navigate("/employer", {
        replace: true,
        state: { flash: `${job.title} is now visible in job search.` },
      });
    } catch (error: unknown) {
      setErrors(fieldErrorsFor(error));
      setSubmitError(error);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageTitle title="Create a job" />
      <header className="page-hero page-hero--compact">
        <div className="container">
          <Link className="back-link" to="/employer">
            <span aria-hidden="true">←</span> Back to employer hub
          </Link>
          <p className="eyebrow">New opportunity</p>
          <h1>Create a job</h1>
          <p>
            Give candidates a clear, honest picture of the role and your team.
          </p>
        </div>
      </header>
      <div className="container page form-page-layout">
        <form
          className="form-card form-card--wide"
          noValidate
          onSubmit={(event) => void handleSubmit(event)}
        >
          {submitError !== null && (
            <Alert
              variant="error"
              title={
                submitError instanceof ApiError && submitError.status === 403
                  ? "You are not authorized to publish jobs"
                  : "Job not published"
              }
              requestId={
                submitError instanceof ApiError
                  ? submitError.requestId
                  : undefined
              }
            >
              {messageForError(submitError)}
            </Alert>
          )}
          <fieldset>
            <legend>Role essentials</legend>
            <div className="form-grid">
              <FormField id="job-title" label="Job title" error={errors.title}>
                <input
                  name="title"
                  autoComplete="off"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                />
              </FormField>
              <FormField
                id="company-name"
                label="Company name"
                error={errors.company_name}
              >
                <input
                  name="company_name"
                  autoComplete="organization"
                  value={companyName}
                  onChange={(event) => setCompanyName(event.target.value)}
                />
              </FormField>
              <FormField
                id="job-location"
                label="Location"
                error={errors.location}
              >
                <input
                  name="location"
                  autoComplete="address-level2"
                  value={location}
                  onChange={(event) => setLocation(event.target.value)}
                />
              </FormField>
              <FormField
                id="employment-type"
                label="Employment type"
                error={errors.employment_type}
              >
                <select
                  name="employment_type"
                  value={employmentType}
                  onChange={(event) => setEmploymentType(event.target.value)}
                >
                  <option value="">Choose a type</option>
                  <option value="full_time">Full time</option>
                  <option value="part_time">Part time</option>
                  <option value="contract">Contract</option>
                  <option value="seasonal">Seasonal</option>
                  <option value="casual">Casual</option>
                </select>
              </FormField>
            </div>
          </fieldset>

          <fieldset>
            <legend>Role details</legend>
            <FormField
              id="job-description"
              label="Description"
              hint="Describe the responsibilities, team and what success looks like."
              error={errors.description}
            >
              <textarea
                name="description"
                rows={8}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            </FormField>
            <FormField
              id="required-skills"
              label="Required skills"
              hint="Separate skills with commas, for example: Guest service, Opera PMS, Team leadership."
              error={errors.required_skills}
            >
              <input
                name="required_skills"
                value={skills}
                onChange={(event) => setSkills(event.target.value)}
              />
            </FormField>
            <label className="checkbox-field" htmlFor="job-active">
              <input
                id="job-active"
                name="active"
                type="checkbox"
                checked={active}
                onChange={(event) => setActive(event.target.checked)}
              />
              <span>
                <strong>Accept applications immediately</strong>
                <small>
                  You can create a closed listing by clearing this option.
                </small>
              </span>
            </label>
          </fieldset>

          <div className="form-actions">
            <Link className="button button--ghost" to="/employer">
              Cancel
            </Link>
            <button
              className="button"
              type="submit"
              disabled={submitting}
              aria-busy={submitting}
            >
              {submitting ? "Publishing…" : "Publish job"}
            </button>
          </div>
        </form>
        <aside className="form-guidance">
          <p className="eyebrow">A stronger job post</p>
          <h2>Help candidates choose well</h2>
          <ul className="check-list">
            <li>Use a title people actually search for.</li>
            <li>Name the location and working pattern clearly.</li>
            <li>Focus required skills on what matters from day one.</li>
            <li>Set clear expectations without sharing sensitive details.</li>
          </ul>
        </aside>
      </div>
    </>
  );
}
