import ReliabilityBar from '../ui/ReliabilityBar.jsx';
import PersonName from '../people/PersonName.jsx';
import { noEmDash } from '../../lib/format.js';
import { accentFor } from '../../lib/categories.js';

// Compact news item used in the home news columns: category kicker in the
// accent color, headline, dek, then the byline meta row.
export default function ArticleCard({ article, onClick }) {
  const a = article;
  const accent = a.accent || accentFor(a.category);
  return (
    <a className="article" style={{ '--accent-c': accent }} onClick={onClick}>
      <div className="a-kicker">
        <span className="k-cat">{a.category || 'National'}</span>
        {a.outlet && <>
          <span className="k-sep">/</span>
          <span className="k-outlet">{a.outlet}</span>
        </>}
      </div>
      <h4>{noEmDash(a.headline)}</h4>
      <div className="dek">{noEmDash(a.dek || '')}</div>
      <div className="a-meta">
        {a.reporter && <span className="by-name"><PersonName name={a.reporter} kind="media" /></span>}
        {a.reliability != null && <ReliabilityBar score={a.reliability} />}
        <span className="ts">{a.timestamp}</span>
      </div>
    </a>
  );
}
