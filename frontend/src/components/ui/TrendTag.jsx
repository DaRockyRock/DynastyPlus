// Up/flat/down momentum indicator used on award candidates and coaches.
export default function TrendTag({ trend = 'flat' }) {
  const t = (trend || 'flat').toLowerCase();
  const arrow = t === 'up' ? '▲' : t === 'down' ? '▼' : '–';
  return <span className={`trend ${t}`}>{arrow} {t}</span>;
}
