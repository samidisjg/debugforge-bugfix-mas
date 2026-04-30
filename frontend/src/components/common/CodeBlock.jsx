export function CodeBlock({ value }) {
  return <pre className="code-block">{value || "No data yet."}</pre>;
}
