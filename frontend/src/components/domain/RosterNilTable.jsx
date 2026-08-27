import Card from '../ui/Card.jsx';
import Button from '../ui/Button.jsx';
import MoneyValue from '../ui/MoneyValue.jsx';
import HeatBar from '../ui/HeatBar.jsx';
import DealbreakerTag from '../ui/DealbreakerTag.jsx';
import PersonName from '../people/PersonName.jsx';

// Roster NIL retention table: each key player with what they expect, what you
// pay now, and their risk of leaving. `onOffer(row)` opens the pay editor.
export default function RosterNilTable({ rows = [], onOffer, title = 'Roster NIL (Retention)' }) {
  return (
    <Card className="nil-table">
      <div className="nt-bar"><h3>{title}</h3><span className="nt-count">{rows.length} players</span></div>
      <div className="nt-head nt-grid-roster">
        <span>Player</span><span>Expected</span><span>Paying</span><span>Risk of Leaving</span><span />
      </div>
      {rows.map((r) => {
        const tone = r.current_nil >= r.expected_nil ? 'pos' : 'neg';
        return (
          <div className="nt-row nt-grid-roster" key={r.id}>
            <div className="nt-name">
              <b><PersonName name={r.name} kind="player" /></b>
              <span className="nt-sub">{r.position} - {r.year}</span>
              <DealbreakerTag value={r.dealbreaker} />
            </div>
            <MoneyValue value={r.expected_nil} />
            <MoneyValue value={r.current_nil} tone={tone} />
            <HeatBar value={r.risk_of_leaving} />
            {onOffer && <Button onClick={() => onOffer(r)}>Adjust</Button>}
          </div>
        );
      })}
    </Card>
  );
}
