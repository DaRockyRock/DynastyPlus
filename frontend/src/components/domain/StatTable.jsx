import Card from '../ui/Card.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';

// True when a stat row has a real, displayable value (drops null/empty/"null"
// rows so the rail never shows "Passing Yards null").
function hasValue(r) {
  if (!r || !r.label) return false;
  const v = r.value;
  if (v == null) return false;
  const s = String(v).trim();
  return s !== '' && s.toLowerCase() !== 'null' && s.toLowerCase() !== 'undefined';
}

// A labeled stat block for article pages ("By the numbers").
export default function StatTable({ rows = [], title = 'By the numbers' }) {
  const clean = (rows || []).filter(hasValue);
  if (!clean.length) return null;
  return (
    <Card className="stat-table">
      <SectionTitle>{title}</SectionTitle>
      <div className="stat-lines">
        {clean.map((r, i) => (
          <div className="stat-line" key={i}>
            <span className="sl-label">{r.label}</span>
            <span className="sl-value">{r.value}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
