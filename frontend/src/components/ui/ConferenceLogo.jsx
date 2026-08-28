import { useState, useEffect } from 'react';
import { confId, confLogoUrl } from '../../lib/conferences.js';
import LogoPlate from './LogoPlate.jsx';

// Conference affiliation logo (game-extracted mark). Accepts a conference `id`
// (ESPN group id) or a conference `name`. Renders nothing if neither resolves
// (e.g. media members). `variant="white"` uses the game's white knockout mark
// for small dark-field placements. The LogoPlate wrapper is now transparent
// (marks sit directly on the field, like the game).
export default function ConferenceLogo({ id, name, size = 18, title, plate = true, variant = '' }) {
  const [failed, setFailed] = useState(false);
  const resolved = id != null ? id : confId(name);
  useEffect(() => { setFailed(false); }, [resolved]);

  const url = confLogoUrl(resolved, variant);
  if (!url || failed) return null;

  if (plate) {
    return (
      <LogoPlate size={size} className="conf-plate" title={title || name || ''}>
        <img className="conf-logo" src={url} alt={title || name || 'conference'} onError={() => setFailed(true)} />
      </LogoPlate>
    );
  }

  return (
    <img
      className="conf-logo"
      src={url}
      width={size}
      height={size}
      alt={title || name || 'conference'}
      title={title || name || ''}
      onError={() => setFailed(true)}
    />
  );
}
