import { useState, useEffect } from 'react';
import { confId, confLogoUrl } from '../../lib/conferences.js';
import LogoPlate from './LogoPlate.jsx';

// Conference affiliation logo. Accepts a conference `id` (ESPN group id) or a
// conference `name`. Renders nothing if neither resolves (e.g. media members).
// All marks render on a legibility plate (LogoPlate) by default so dark
// conference logo elements stay readable on the dark field. Pass plate={false}
// only where a plate is genuinely redundant (e.g. an already-lit surface).
export default function ConferenceLogo({ id, name, size = 18, title, plate = true }) {
  const [failed, setFailed] = useState(false);
  const resolved = id != null ? id : confId(name);
  useEffect(() => { setFailed(false); }, [resolved]);

  const url = confLogoUrl(resolved);
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
