// A single numbered instruction in the setup guide. `n` is the step number,
// `title` the heading, and children the body (copy, links, code snippets).
export default function GuideStep({ n, title, children }) {
  return (
    <li className="guide-step">
      <span className="gs-num">{n}</span>
      <div className="gs-body">
        {title && <span className="gs-title">{title}</span>}
        {children && <div className="gs-text">{children}</div>}
      </div>
    </li>
  );
}
