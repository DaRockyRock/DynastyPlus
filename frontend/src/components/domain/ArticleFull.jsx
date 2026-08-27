import Card from '../ui/Card.jsx';
import Chip from '../ui/Chip.jsx';
import ReliabilityBar from '../ui/ReliabilityBar.jsx';
import PersonName from '../people/PersonName.jsx';
import { noEmDash } from '../../lib/format.js';

// Full-body article used in the News Feed columns. Clickable when `onClick`
// is provided (opens the full article page).
export default function ArticleFull({ article, onClick }) {
  const a = article;
  return (
    <Card
      className={`article-full${onClick ? ' clickable' : ''}`}
      style={{ borderLeft: `3px solid ${a.accent || '#64748b'}` }}
      onClick={onClick}
    >
      <div className="a-top">
        <Chip category={a.category || 'National'} accent={a.accent} />
        <span className="ts">{a.timestamp}</span>
      </div>
      <h3 className="af-headline">{noEmDash(a.headline)}</h3>
      <div className="dek">{noEmDash(a.dek || '')}</div>
      <div className="article-body">{noEmDash(a.body || '')}</div>
      <div className="a-meta">
        {a.outlet && <span className="outlet">{a.outlet}</span>}
        {a.outlet && a.reporter && <span className="sep">/</span>}
        {a.reporter && <span className="by-name"><PersonName name={a.reporter} kind="media" /></span>}
        {a.reliability != null && <span className="rel-wrap"><ReliabilityBar score={a.reliability} /></span>}
      </div>
    </Card>
  );
}
