interface AlertProps {
  children: React.ReactNode;
  variant?: "error" | "success" | "info";
  title?: string;
  requestId?: string;
  onRetry?: () => void;
}

export function Alert({
  children,
  variant = "info",
  title,
  requestId,
  onRetry,
}: AlertProps) {
  return (
    <div
      className={`alert alert--${variant}`}
      role={variant === "error" ? "alert" : "status"}
      aria-live={variant === "error" ? "assertive" : "polite"}
    >
      <div className="alert__content">
        {title && <strong className="alert__title">{title}</strong>}
        <div>{children}</div>
        {requestId && (
          <small className="alert__request-id">Request ID: {requestId}</small>
        )}
      </div>
      {onRetry && (
        <button
          className="button button--small button--secondary"
          onClick={onRetry}
        >
          Retry
        </button>
      )}
    </div>
  );
}
