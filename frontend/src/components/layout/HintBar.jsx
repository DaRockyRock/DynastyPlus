import KeyGlyph from '../ui/KeyGlyph.jsx';
import { GearIcon } from '../ui/icons.jsx';

// The game's bottom action-hint strip: full-width near-black bar with
// key-glyph + label hints on the left and a quiet brand readout on the right.
// `hints` = [{ key?, glyph?, label, onClick?, disabled?, dark? }]. `glyph`
// uses the game's real keyboard button art (/game-assets/ui/keys); `key` is a
// text key cap fallback. Items with onClick render as buttons. `onSettings`
// adds a leading gear button (the Customize entry point), so it lives in the
// bar rather than floating over it.
export default function HintBar({ hints = [], brand = 'DYNASTY+ COMPANION', onSettings }) {
  return (
    <footer className="hintbar">
      {onSettings && (
        <button className="hint-item hint-gear" onClick={onSettings} title="Customize" aria-label="Customize">
          <GearIcon />
          Customize
        </button>
      )}
      {hints.map((h) => {
        const cap = h.glyph
          ? <KeyGlyph name={h.glyph} label={h.key || h.label} />
          : <span className={`hint-key${h.dark ? ' dark' : ''}`}>{h.key}</span>;
        return h.onClick ? (
          <button key={h.label} className="hint-item" onClick={h.onClick} disabled={h.disabled}>
            {cap}
            {h.label}
          </button>
        ) : (
          <span key={h.label} className="hint-item">
            {cap}
            {h.label}
          </span>
        );
      })}
      <span className="hb-spacer" />
      <span className="hb-brand">{brand}</span>
    </footer>
  );
}
