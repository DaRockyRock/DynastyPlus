// Indicates whether a module's content came from the LLM, mock data, or is
// static. Mirrors the `source` field returned by every generation module.
export default function SourcePill({ source }) {
  const s = (source || 'mock').toLowerCase();
  const label = s === 'llm' ? 'LLM' : s === 'static' ? 'STATIC' : 'MOCK';
  return <span className={`source-pill ${s}`}>{label}</span>;
}
