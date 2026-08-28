import PanelCard from '../ui/PanelCard.jsx';
import ToggleSwitch from '../ui/ToggleSwitch.jsx';

// The master on/off switch for the custom playoff bracket automation, shown on
// both the Playoff Format editor and the Playoff Bracket tab.
//
// OFF (the opt-in default) means CFB 27 runs its own native 12-team playoff and
// Dynasty+ writes nothing to the bracket: no "update dynasty file" prompts and
// no rewind loop. Custom conference alignment and custom poll rankings still
// reach the game, so they seed the native bracket. ON hands the postseason to
// the format the user built (any field size), written into the save round by
// round. Same shape as the recruiting tool's opt-in switch.
//
// ToggleSwitch has no disabled prop, so a click is swallowed while `busy` to
// avoid firing the config write twice on a fast double toggle.
export default function PlayoffAutomationToggle({ enabled = false, onChange, busy = false }) {
  return (
    <PanelCard title="Custom playoff bracket">
      <div className="pfe-row">
        <span className="pfe-row-label">
          {enabled
            ? 'On: Dynasty+ runs your custom bracket'
            : 'Off: CFB 27 runs its native 12-team playoff'}
          <span className="pfe-row-sub">
            {enabled
              ? 'Your format is written into the save round by round. Use this for any field that is not the standard 12-team bracket.'
              : 'Dynasty+ leaves the bracket alone (no update prompts). Your conference alignment and custom poll rankings still seed the game\'s own playoff.'}
          </span>
        </span>
        <ToggleSwitch checked={enabled} onChange={busy ? undefined : onChange} />
      </div>
    </PanelCard>
  );
}
