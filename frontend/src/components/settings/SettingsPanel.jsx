import Button from '../ui/Button.jsx';
import { RefreshIcon } from '../ui/icons.jsx';

// Frame for the active section: title, blurb, a save/reset action cluster with
// a dirty/saved status pill, and the section editor as children.
export default function SettingsPanel({ section, dirty, saving, onSave, onReset, children }) {
  return (
    <div className="set-content-inner">
      <div className="set-panel-head">
        <div className="ph-text">
          <h2>{section.label}</h2>
          {section.blurb && <div className="blurb">{section.blurb}</div>}
        </div>
        <div className="ph-actions">
          {dirty ? <span className="set-dirty">Unsaved</span> : <span className="set-saved">Saved</span>}
          <Button variant="compact" onClick={onReset} title="Revert this section to the default">
            <RefreshIcon size={13} />Reset
          </Button>
          <Button variant="accent" onClick={onSave} disabled={!dirty || saving} spinning={saving}>
            {saving ? 'Saving' : 'Save'}
          </Button>
        </div>
      </div>
      {children}
    </div>
  );
}
