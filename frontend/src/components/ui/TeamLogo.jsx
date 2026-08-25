import { useState, useEffect } from 'react';
import { logoUrl, hexColor } from '../../lib/format.js';
import LogoPlate from './LogoPlate.jsx';

// The single team-mark component used everywhere. Always renders the real ESPN
// logo on a legibility plate (LogoPlate) so dark logo elements stay readable on
// the dark field; pass plate={false} where the mark already sits in its own
// frame (e.g. the top-bar HUD slot). If the image fails to load (or no espnId is
// known), it falls back to a neutral monogram chip. No helmets anywhere.
export default function TeamLogo({ espnId, abbr, name, color, size = 40, title, plate = true, logo = '' }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => { setFailed(false); }, [espnId, logo]);

  // A custom uploaded logo (from the Customize flow) overrides the ESPN mark.
  const url = logo || logoUrl(espnId);
  const label = (abbr || (name ? name.replace(/[^A-Za-z]/g, '').slice(0, 3) : '') || '').toUpperCase();
  const tip = title || name || label;

  if (!url || failed) {
    return (
      <span
        className="team-mono"
        style={{ width: size, height: size, fontSize: Math.max(9, size * 0.32), background: hexColor(color, '#243044') }}
        title={tip}
      >
        {label.slice(0, 3) || '--'}
      </span>
    );
  }

  if (plate) {
    return (
      <LogoPlate size={size} title={tip}>
        <img src={url} alt={tip} onError={() => setFailed(true)} />
      </LogoPlate>
    );
  }

  return (
    <span className="team-logo" style={{ width: size, height: size }} title={tip}>
      <img src={url} alt={tip} onError={() => setFailed(true)} />
    </span>
  );
}
