import { logoUrl } from '../../lib/format.js';
import { confLogoUrl } from '../../lib/conferences.js';

// The faint logo(s) stamped behind a top-stories slide. The backend tags each story
// with the marks it references (`marks.kind` + conference + teams) and this turns
// that into the slide's backdrop:
//   matchup    -> the two team logos with a slanted VS
//   group      -> a cluster of every team named
//   conference -> the conference mark
//   team       -> a single team logo
// When a story references nothing, it falls back to `fallbackUrl` (the user's team
// on program slides), matching the old single-logo watermark. Raw images, no plates,
// so they read as a watermark rather than a foreground bug.
const teamLogo = (t) => t.logo || logoUrl(t.espn_id);

// How many logos sit on each row so a cluster reads cleanly: a row, a 2x2, a 3+2,
// or a 3x3 (partial rows stay centered).
function rowPlan(n) {
  if (n <= 3) return [n];
  if (n === 4) return [2, 2];
  if (n === 5) return [3, 2];
  return [3, 3];
}

export default function StoryWatermark({ marks, fallbackUrl = null }) {
  const kind = marks?.kind;
  const teams = marks?.teams || [];
  const conference = marks?.conference || null;

  if (kind === 'matchup' && teams.length >= 2) {
    const [a, b] = teams;
    return (
      <div className="slide-watermark wm-matchup">
        <img className="wm-logo" src={teamLogo(a)} alt="" />
        <span className="wm-vs">VS</span>
        <img className="wm-logo" src={teamLogo(b)} alt="" />
      </div>
    );
  }

  if (kind === 'group' && teams.length >= 2) {
    const list = teams.slice(0, 6);
    let cursor = 0;
    const rows = rowPlan(list.length).map((count) => {
      const slice = list.slice(cursor, cursor + count);
      cursor += count;
      return slice;
    });
    return (
      <div className={`slide-watermark wm-group wm-group-${list.length}`}>
        {rows.map((slice, ri) => (
          <div className="wm-row" key={ri}>
            {slice.map((t, i) => (
              <img key={t.espn_id || `${ri}-${i}`} className="wm-logo" src={teamLogo(t)} alt="" />
            ))}
          </div>
        ))}
      </div>
    );
  }

  if (kind === 'conference' && conference) {
    return <img className="slide-watermark wm-single" src={confLogoUrl(conference.id)} alt="" />;
  }

  if (kind === 'team' && teams.length) {
    return <img className="slide-watermark wm-single" src={teamLogo(teams[0])} alt="" />;
  }

  return fallbackUrl ? <img className="slide-watermark wm-single" src={fallbackUrl} alt="" /> : null;
}
