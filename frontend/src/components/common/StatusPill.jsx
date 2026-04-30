export function StatusPill({ tone = "idle", children }) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}
