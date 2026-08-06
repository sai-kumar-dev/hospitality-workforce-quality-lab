import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ApiError, fieldErrorsFor, messageForError } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { Alert } from "../components/Alert";
import { FormField } from "../components/FormField";
import { PageTitle } from "../components/PageTitle";

interface RegistrationErrors {
  full_name?: string;
  email?: string;
  password?: string;
  confirm_password?: string;
}

export function RegisterPage() {
  const { user, register, homeForRole } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<RegistrationErrors>({});
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate replace to={homeForRole(user.role)} />;

  function validate(): RegistrationErrors {
    const nextErrors: RegistrationErrors = {};
    if (fullName.trim().length < 2)
      nextErrors.full_name = "Enter your full name.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      nextErrors.email = "Enter a valid email address.";
    if (password.length < 8) nextErrors.password = "Use at least 8 characters.";
    if (confirmPassword !== password)
      nextErrors.confirm_password = "Passwords do not match.";
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
      await register({
        full_name: fullName.trim(),
        email: email.trim().toLowerCase(),
        password,
      });
      navigate("/candidate", {
        replace: true,
        state: {
          flash: "Your candidate profile is ready. Welcome to ShiftBridge.",
        },
      });
    } catch (error: unknown) {
      setErrors(fieldErrorsFor(error));
      setSubmitError(error);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="auth-page auth-page--register">
      <PageTitle title="Join as a candidate" />
      <div className="container auth-layout">
        <div className="auth-intro">
          <p className="eyebrow">A better next shift starts here</p>
          <h1>Create your candidate profile</h1>
          <p className="lead">
            One focused profile gives you access to hospitality opportunities
            across trusted local teams.
          </p>
          <ol className="step-list">
            <li>
              <span>1</span> Create your secure account
            </li>
            <li>
              <span>2</span> Find a role that fits
            </li>
            <li>
              <span>3</span> Apply with a short note
            </li>
          </ol>
        </div>

        <div className="form-card">
          <h2>Your details</h2>
          <p className="form-card__intro">All fields are required.</p>
          {submitError !== null && (
            <Alert
              variant="error"
              title="We could not create your account"
              requestId={
                submitError instanceof ApiError
                  ? submitError.requestId
                  : undefined
              }
            >
              {messageForError(submitError)}
            </Alert>
          )}
          <form noValidate onSubmit={(event) => void handleSubmit(event)}>
            <FormField
              id="register-name"
              label="Full name"
              error={errors.full_name}
            >
              <input
                type="text"
                name="full_name"
                autoComplete="name"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
              />
            </FormField>
            <FormField
              id="register-email"
              label="Email address"
              error={errors.email}
            >
              <input
                type="email"
                name="email"
                autoComplete="email"
                inputMode="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </FormField>
            <FormField
              id="register-password"
              label="Password"
              hint="Use at least 8 characters."
              error={errors.password}
            >
              <input
                type="password"
                name="password"
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </FormField>
            <FormField
              id="register-confirm-password"
              label="Confirm password"
              error={errors.confirm_password}
            >
              <input
                type="password"
                name="confirm_password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
              />
            </FormField>
            <button
              className="button button--full"
              type="submit"
              disabled={submitting}
              aria-busy={submitting}
            >
              {submitting ? "Creating account…" : "Create account"}
            </button>
          </form>
          <p className="form-card__footer">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </div>
    </section>
  );
}
