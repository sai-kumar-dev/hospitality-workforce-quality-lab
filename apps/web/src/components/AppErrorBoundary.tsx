import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryState {
  failed: boolean;
}

export class AppErrorBoundary extends Component<
  { children: ReactNode },
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { failed: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (import.meta.env.DEV) {
      console.error("ShiftBridge render failure", error, info.componentStack);
    }
  }

  render() {
    if (!this.state.failed) return this.props.children;

    return (
      <main className="fatal-error">
        <section className="container page page--narrow">
          <p className="eyebrow">Unexpected application error</p>
          <h1>ShiftBridge needs a fresh start</h1>
          <p className="lead">
            We could not display this page safely. Reload the application to try
            again; your submitted information has not been resent.
          </p>
          <button className="button" onClick={() => window.location.reload()}>
            Reload ShiftBridge
          </button>
        </section>
      </main>
    );
  }
}
