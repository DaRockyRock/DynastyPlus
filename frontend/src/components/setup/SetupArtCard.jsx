import PanelCard from '../ui/PanelCard.jsx';
import Button from '../ui/Button.jsx';
import ProgressBar from '../ui/ProgressBar.jsx';
import StatusDot from '../ui/StatusDot.jsx';
import Callout from '../ui/Callout.jsx';
import { UploadIcon } from '../ui/icons.jsx';

// Human-readable label for each extraction stage the backend reports.
const STAGE_LABEL = {
  starting: 'Starting',
  teams: 'Team logos and helmets',
  conferences: 'Conference logos',
  fonts: 'Game fonts',
  ui: 'Interface icons',
  done: 'Finishing up',
};

// The "game art" panel of the Setup screen: shows whether art has been pulled
// from the install, and a one-click extract with a live progress bar. The art
// is read from the user's own game and never shipped, so this always runs on the
// user's machine. Presentational only.
export default function SetupArtCard({
  present = false,
  installFound = false,
  extracting = false,
  stage,
  done = 0,
  total = 0,
  error,
  onExtract,
}) {
  const pct = total ? Math.round((done / total) * 100) : (extracting ? 6 : 0);
  const step = total ? Math.min(done + (stage === 'done' ? 0 : 1), total) : 0;

  return (
    <PanelCard title="Game art" className="setup-art">
      <p className="setup-row-hint">
        Dynasty+ shows the real team logos, helmets, and fonts from your copy of
        College Football 27. They are read from your installed game and stay on
        your computer.
      </p>
      <div className="setup-row-status">
        <StatusDot tone={present ? 'live' : 'idle'} pulse={present} />
        <span className="setup-row-state">
          {present ? 'Game art installed' : 'Not installed yet'}
        </span>
      </div>

      {extracting ? (
        <div className="setup-art-progress">
          <ProgressBar value={pct} />
          <span className="setup-art-stage">
            {STAGE_LABEL[stage] || 'Working'}{total ? ` (${step}/${total})` : ''}
          </span>
        </div>
      ) : (
        <Button variant="accent" icon={<UploadIcon />} onClick={onExtract} disabled={!installFound}>
          {present ? 'Re-extract game art' : 'Extract game art'}
        </Button>
      )}

      {!installFound && !extracting && (
        <Callout tone="warn" title="Game not found">
          Point Dynasty+ at your College Football 27 install above, then extract.
        </Callout>
      )}
      {error && !extracting && (
        <Callout tone="warn" title="Extraction did not finish">{error}</Callout>
      )}
    </PanelCard>
  );
}
