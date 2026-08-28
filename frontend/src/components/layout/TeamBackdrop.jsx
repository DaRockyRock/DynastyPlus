import { useEffect, useState } from 'react';
import { teamAsset } from '../../lib/format.js';

// The team's own dynasty-hub background from the game (extracted stadium art,
// teams/<espnId>/hub-bg.jpg), rendered as a fixed layer under the whole app so
// every screen sits on the program's real backdrop, exactly like the game's
// dynasty hub. Falls back to nothing (the team-color field in tokens.css shows
// through) when the art is missing, so it is safe for every team.
export default function TeamBackdrop({ espnId }) {
  const src = espnId ? teamAsset(espnId, 'hub-bg') : null;
  const [failed, setFailed] = useState(false);
  useEffect(() => { setFailed(false); }, [src]);
  if (!src || failed) return null;
  return (
    <div className="team-backdrop" aria-hidden="true">
      <img src={src} alt="" onError={() => setFailed(true)} />
    </div>
  );
}
