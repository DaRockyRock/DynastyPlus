// Indicates whether a Tools view uses local sample data or static data.
export default function SourcePill({ source }) {
  const s = (source || 'mock').toLowerCase();
  const normalized = s === 'static' ? 'static' : 'mock';
  const label = normalized === 'static' ? 'STATIC' : 'LOCAL';
  return <span className={`source-pill ${normalized}`}>{label}</span>;
}
