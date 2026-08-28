import PanelCard from '../ui/PanelCard.jsx';
import Button from '../ui/Button.jsx';
import Select from '../ui/Select.jsx';
import StatusDot from '../ui/StatusDot.jsx';
import { FolderIcon } from '../ui/icons.jsx';

// One folder row in the Setup screen: a labeled location (the saves folder or
// the game install) with a found/not-found indicator, the current path, an
// optional dropdown of auto-detected candidates, and a native "Browse..."
// button (Electron). Presentational only.
export default function SetupPathRow({
  title,
  hint,
  path,
  found = false,
  options = [],
  onChoose,
  onBrowse,
  browsing = false,
}) {
  const hasOptions = Array.isArray(options) && options.length > 0;
  return (
    <PanelCard title={title} className="setup-row">
      {hint && <p className="setup-row-hint">{hint}</p>}
      <div className="setup-row-status">
        <StatusDot tone={found ? 'live' : 'idle'} pulse={found} />
        <span className="setup-row-state">{found ? 'Found' : 'Not found yet'}</span>
      </div>
      <div className="setup-row-path">{path || 'No folder selected'}</div>
      <div className="setup-row-actions">
        {hasOptions && (
          <Select
            options={options.map((p) => ({ value: p, label: p }))}
            value={path}
            onValueChange={(v) => onChoose?.(v)}
            aria-label={`Detected ${title}`}
          />
        )}
        {onBrowse && (
          <Button
            variant="action"
            icon={<FolderIcon />}
            onClick={onBrowse}
            disabled={browsing}
            spinning={browsing}
          >
            Browse...
          </Button>
        )}
      </div>
    </PanelCard>
  );
}
