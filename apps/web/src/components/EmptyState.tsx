interface EmptyStateProps {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}

export function EmptyState({ title, children, action }: EmptyStateProps) {
  return (
    <section className="empty-state" aria-labelledby="empty-state-title">
      <span className="empty-state__mark" aria-hidden="true">
        SB
      </span>
      <h2 id="empty-state-title">{title}</h2>
      <p>{children}</p>
      {action && <div className="empty-state__action">{action}</div>}
    </section>
  );
}
