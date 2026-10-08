export default function Panel({ title, right, children, className = "" }) {
  return (
    <section className={`rounded-xl border border-navy-700 bg-navy-900 p-5 ${className}`}>
      {(title || right) && (
        <header className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="text-sm font-medium text-mute">{title}</h2>}
          {right}
        </header>
      )}
      {children}
    </section>
  );
}

export function Notice({ children, tone = "info" }) {
  const cls = tone === "error" ? "border-danger/40 text-danger" : "border-navy-600 text-mute";
  return <div className={`rounded-lg border bg-navy-800 px-4 py-3 text-sm ${cls}`}>{children}</div>;
}
