// A real keyboard key glyph from the game's button-icon library
// (/game-assets/ui/keys/<name>.png: enter, escape, tab, shift, a-z, 0-9, ...).
// Falls back to a text key cap when the glyph is missing.
import { useState } from 'react';

export default function KeyGlyph({ name, label, size = 20 }) {
  const [failed, setFailed] = useState(false);
  if (!name || failed) {
    return <span className="hint-key dark">{label || name}</span>;
  }
  return (
    <img
      className="key-glyph"
      src={`/game-assets/ui/keys/${name}.png`}
      width={size}
      height={size}
      alt={label || name}
      onError={() => setFailed(true)}
    />
  );
}
