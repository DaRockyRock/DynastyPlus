import TeamLogo from '../ui/TeamLogo.jsx';
import Chip from '../ui/Chip.jsx';
import { noEmDash } from '../../lib/format.js';

// An embedded reference attached to a feed post: the thing the post is reacting
// to. Renders by `ref.type`. An article card opens the full reader; a game card
// shows the score with team logos; ranking/recruit/other render as compact cards.
export default function FeedRefCard({ refData, onOpenArticle }) {
  const r = refData;
  if (!r || !r.type) return null;

  if (r.type === 'article') {
    const open = (e) => {
      e.stopPropagation();
      if (onOpenArticle && r.article) onOpenArticle(r.article);
    };
    return (
      <button type="button" className="feed-ref article" style={{ borderLeftColor: r.accent || '#64748b' }} onClick={open}>
        {r.category && <Chip category={r.category} accent={r.accent} />}
        <div className="fr-headline">{noEmDash(r.headline || '')}</div>
        <div className="fr-byline">
          {r.outlet && <span className="fr-outlet">{r.outlet}</span>}
          {r.outlet && r.reporter && <span className="fr-sep">/</span>}
          {r.reporter && <span className="fr-by">{r.reporter}</span>}
        </div>
      </button>
    );
  }

  if (r.type === 'game') {
    const scoreParts = (r.score || '').match(/^(\d+)-(\d+)$/);
    const usScore = scoreParts ? scoreParts[1] : null;
    const themScore = scoreParts ? scoreParts[2] : null;
    const sideNote = !scoreParts ? (r.score || r.spread || null) : null;
    return (
      <div className="feed-ref game">
        <div className="fr-game-header">
          <span className="fr-label">{r.label || 'GAME'}</span>
          {sideNote && <span className="fr-side-note">{sideNote}</span>}
        </div>
        <div className="fr-score">
          <div className="fr-team-row">
            <TeamLogo espnId={r.us_espn_id} name={r.us} size={22} />
            <span className="fr-tn">{r.us}</span>
            {usScore != null && <span className="fr-pts">{usScore}</span>}
          </div>
          <div className="fr-team-row">
            <TeamLogo espnId={r.them_espn_id} name={r.them} size={22} />
            <span className="fr-tn">{r.them}</span>
            {themScore != null && <span className="fr-pts">{themScore}</span>}
          </div>
        </div>
        {(r.tv || r.rank_matchup) && <div className="fr-sub">{noEmDash(r.rank_matchup || r.tv || '')}</div>}
      </div>
    );
  }

  if (r.type === 'ranking') {
    const items = r.items || [];
    return (
      <div className="feed-ref ranking">
        <span className="fr-label">{r.label || 'Rankings'}</span>
        <ol className="fr-rank-list">
          {items.slice(0, 5).map((it, i) => (
            <li key={i}>
              <span className="fr-rk">{it.rank ?? i + 1}</span>
              {it.espn_id != null && <TeamLogo espnId={it.espn_id} name={it.team} size={18} plate={false} />}
              <span className="fr-rn">{it.name || it.team}{it.position ? ` (${it.position})` : ''}</span>
            </li>
          ))}
        </ol>
      </div>
    );
  }

  if (r.type === 'confrace') {
    const teams = r.teams || [];
    if (!teams.length) return null;
    return (
      <div className="feed-ref confrace">
        <span className="fr-label">{r.label || 'Conference race'}</span>
        <ol className="fr-rank-list">
          {teams.slice(0, 5).map((it, i) => (
            <li key={i}>
              <span className="fr-rk">{i + 1}</span>
              {it.espn_id != null && <TeamLogo espnId={it.espn_id} name={it.team} size={18} plate={false} />}
              <span className="fr-rn">{it.team}{it.overall ? ` (${it.overall})` : ''}</span>
            </li>
          ))}
        </ol>
      </div>
    );
  }

  if (r.type === 'recruit') {
    return (
      <div className="feed-ref recruit">
        <span className="fr-stars">{r.stars ? `${r.stars}-star` : 'Prospect'}</span>
        <span className="fr-rn">{r.position} {r.name}</span>
        {r.status && <span className={`fr-tag ${r.status}`}>{r.status === 'commit' ? 'Committed' : 'Target'}</span>}
        {r.hometown && <span className="fr-sub">{noEmDash(r.hometown)}</span>}
      </div>
    );
  }

  // portal / hot_seat / anything else: a compact generic card.
  const title = r.type === 'portal'
    ? `${r.name} to ${r.to || 'the portal'}`
    : r.type === 'hot_seat'
      ? `${r.coach} on the hot seat`
      : (r.title || r.label || '');
  const sub = r.type === 'portal' ? `Transfer portal (${r.position || ''})`
    : r.type === 'hot_seat' ? noEmDash(r.note || '') : (r.subtitle || '');
  if (!title) return null;
  return (
    <div className={`feed-ref ${r.type}`}>
      <div className="fr-headline">{noEmDash(title)}</div>
      {sub && <div className="fr-sub">{sub}</div>}
    </div>
  );
}
