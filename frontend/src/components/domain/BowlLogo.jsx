import { useEffect, useState } from 'react';

// Real bowl mark extracted from the local CFB 27 install. A typographic mark
// keeps the card complete when the user has not extracted that particular art.
export default function BowlLogo({ asset, name, size = 108 }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [asset]);
  if (!asset || failed) {
    return (
      <span className="bowl-logo-fallback" style={{ '--bowl-logo-size': `${size}px` }}>
        <strong>{name || 'Bowl Game'}</strong>
        <small>CFB 27</small>
      </span>
    );
  }
  return (
    <img
      className="bowl-logo"
      style={{ '--bowl-logo-size': `${size}px` }}
      src={`/game-assets/bowls/${asset}.png`}
      alt={`${name || 'Bowl game'} logo`}
      onError={() => setFailed(true)}
    />
  );
}
