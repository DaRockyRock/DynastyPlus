import ToggleSwitch from '../ui/ToggleSwitch.jsx';

// The hero the postseason pages collapse to when the custom playoff automation
// is off (the opt-in default). Per the product call, the WHOLE page disappears
// and only this remains: the switch front and center so the user knows exactly
// where to turn the tool back on, one line of explanation, and a quiet list of
// what still applies while the game runs its own playoff.
//
// `onEnable` fires when the user flips the switch on; `busy` swallows clicks
// while the config write is in flight.
export default function PlayoffOffState({ onEnable, busy = false }) {
  return (
    <div className="pfo-off">
      <section className="pfo-card">
        <span className="pfo-eyebrow">Dynasty+ Postseason</span>
        <h2 className="pfo-title">Custom Playoff Is Off</h2>
        <p className="pfo-lede">
          CFB 27 is running its own College Football Playoff. Dynasty+ leaves
          the postseason untouched: no bracket writes and no update prompts.
        </p>
        <div className={`pfo-switch${busy ? ' busy' : ''}`}>
          <ToggleSwitch
            checked={false}
            label="Turn on custom playoff"
            onChange={() => onEnable?.()}
          />
        </div>
        <div className="pfo-still">
          <span className="pfo-still-item">
            <span className="pfo-check">✓</span>
            Custom polls still seed the game's bracket (push before bowl
            season; once the bracket is set they only relabel seeds)
          </span>
          <span className="pfo-still-item">
            <span className="pfo-check">✓</span>
            Conference changes still apply
          </span>
        </div>
      </section>
    </div>
  );
}
