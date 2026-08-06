import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ApiError, fieldErrorsFor, messageForError } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { Alert } from "../components/Alert";
import { FormField } from "../components/FormField";
import { PageTitle } from "../components/PageTitle";

interface LoginErrors {
  email?: string;
  password?: string;
}

function destinationFromState(state: unknown): string | null {
  if (
    typeof state === "object" &&
    state !== null &&
    "from" in state &&
    typeof state.from === "string" &&
    state.from.startsWith("/")
  ) {
    return state.from;
  }
  return null;
}

export function LoginPage() {
  const { user, login, homeForRole } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<LoginErrors>({});
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate replace to={homeForRole(user.role)} />;

  function validate(): LoginErrors {
    const nextErrors: LoginErrors = {};
    if (!email.trim()) nextErrors.email = "Enter your email address.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      nextErrors.email = "Enter a valid email address.";
    if (!password) nextErrors.password = "Enter your password.";
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
      const authenticatedUser = await login({
        email: email.trim().toLowerCase(),
        password,
      });
      navigate(
        destinationFromState(location.state) ??
          homeForRole(authenticatedUser.role),
        { replace: true },
      );
    } catch (error: unknown) {
      setErrors(fieldErrorsFor(error));
      setSubmitError(error);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="auth-page">
      <PageTitle title="Sign in" />
      <div className="container auth-layout">
        <div className="auth-intro">
          <p className="eyebrow">Welcome to ShiftBridge</p>
          <h1>Welcome back</h1>
          <p className="lead">
            Pick up where you left off—whether you are finding your next role or
            building a great hospitality team.
          </p>
          <div className="auth-intro__note">
            <strong>Local demo</strong>
            <p>
              Use one of the seeded accounts documented in the project README.
            </p>
          </div>
        </div>

        <div className="form-card">
          <h2>Sign in to your account</h2>
          <p className="form-card__intro">
            Enter your ShiftBridge account details.
          </p>
          {submitError !== null && (
            <Alert
              variant="error"
              title={
                submitError instanceof ApiError && submitError.status === 401
                  ? "Sign in failed"
                  : "We could not sign you in"
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
          <form noValidate onSubmit={(event) => void handleSubmit(event)}>
            <FormField
              id="login-email"
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
              id="login-password"
              label="Password"
              error={errors.password}
            >
              <input
                type="password"
                name="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </FormField>
            <button
              className="button button--full"
              type="submit"
              disabled={submitting}
              aria-busy={submitting}
            >
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="form-card__footer">
            Looking for hospitality work?{" "}
            <Link to="/register">Create a candidate account</Link>
          </p>
        </div>
      </div>
    </section>
  );
}
