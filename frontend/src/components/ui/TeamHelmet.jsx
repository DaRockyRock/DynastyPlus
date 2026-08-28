import { useState } from 'react';
import TeamLogo from './TeamLogo.jsx';
import { teamAsset } from '../../lib/format.js';

// A team's game-rendered helmet (extracted from the CFB 27 install). `side`
// picks the facing: 'right' for the away/left slot, 'left' for the home/right
// slot, matching the game's matchup splash. Falls back to the team logo when
// the helmet art is missing.
export default function TeamHelmet({ espnId, abbr, name, color, side = 'right', size = 96, title }) {
  const [failed, setFailed] = useState(false);
  // The extracted art is named by the SLOT it fills in the game's own splash,
  // not by facing: helmet-left.png (left slot) faces right, helmet-right.png
  // (right slot) faces left. `side` here is the facing we want, so the names
  // cross over; mapping them straight renders every matchup facing apart.
  const url = teamAsset(espnId, side === 'left' ? 'helmet-right' : 'helmet-left');
  if (!url || failed) {
    return <TeamLogo espnId={espnId} abbr={abbr} name={name} color={color} size={size} plate={false} />;
  }
  return (
    <img
      className="hm-helmet"
      style={{ '--hm-size': `${size}px` }}
      src={url}
      alt={title || name || abbr || 'helmet'}
      title={title || name}
      onError={() => setFailed(true)}
    />
  );
}
