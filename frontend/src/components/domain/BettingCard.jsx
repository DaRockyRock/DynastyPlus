import Card from '../ui/Card.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';

// Betting lines + futures for an article page. `betting` = { game, futures }.
export default function BettingCard({ betting }) {
  if (!betting) return null;
  const { game, futures } = betting;
  return (
    <Card className="betting-card">
      <SectionTitle>Odds &amp; Futures</SectionTitle>
      {game && (
        <div className="odds-game">
          <div className="odds-matchup">{game.matchup}</div>
          <div className="odds-row"><span>Spread</span><b>{game.spread}</b></div>
          <div className="odds-row"><span>Total</span><b>{game.total}</b></div>
          <div className="odds-row"><span>Moneyline</span><b>{game.moneyline}</b></div>
        </div>
      )}
      {(futures || []).length > 0 && (
        <div className="odds-futures">
          {futures.map((f, i) => (
            <div className="odds-row" key={i}><span>{f.label}</span><b>{f.value}</b></div>
          ))}
        </div>
      )}
    </Card>
  );
}
