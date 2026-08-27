import { useState, useEffect } from 'react';
import { initials } from '../../lib/format.js';

// Circular avatar. With `src` (a custom uploaded photo) it shows the image,
// falling back to initials if the image fails to load. `gradient` uses the
// team-colored gradient used by phone contacts; otherwise a neutral surface.
export default function Avatar({ name, label, size = 40, gradient = false, src = '' }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => { setFailed(false); }, [src]);

  const text = label || initials(name);
  const style = { width: size, height: size, fontSize: Math.max(11, size * 0.34) };
  if (gradient) style.background = 'linear-gradient(135deg, var(--team), #7a0f1f)';

  if (src && !failed) {
    return (
      <span className="avatar" style={{ ...style, overflow: 'hidden' }}>
        <img src={src} alt={name || ''} onError={() => setFailed(true)}
          style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
      </span>
    );
  }
  return <span className="avatar" style={style}>{text}</span>;
}
