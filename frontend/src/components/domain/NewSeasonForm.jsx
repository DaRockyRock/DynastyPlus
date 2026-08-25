import { useState } from 'react';
import Card from '../ui/Card.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import FormField from '../ui/FormField.jsx';
import TextInput from '../ui/TextInput.jsx';
import Button from '../ui/Button.jsx';
import { PlayIcon } from '../ui/icons.jsx';
import TeamSelect from './TeamSelect.jsx';

// Spin up a fresh simulated FBS season. Pick your program, then year + optional
// seed; the same seed and year reproduce the same season. Used when no season is
// active. The team picker swaps the user's program (identity + its real local
// customization) before kickoff; once a season is running it cannot change.
export default function NewSeasonForm({
  defaultYear = 2027,
  busy = false,
  onStart,
  teams = [],
  team = '',
  onSelectTeam,
  teamBusy = false,
}) {
  const [year, setYear] = useState(String(defaultYear));
  const [seed, setSeed] = useState('');

  const start = () => {
    const y = parseInt(year, 10);
    if (!y) return;
    onStart?.(y, seed ? parseInt(seed, 10) : null);
  };

  return (
    <Card className="newseason-card">
      <SectionTitle>Start a New Season</SectionTitle>
      <p className="ns-help">
        Builds a full simulated FBS season: every team gets a rating and a schedule, then you
        advance week to week. Records, polls, standings, and stats all emerge from the games.
      </p>
      <div className="ns-fields">
        {teams.length > 0 && (
          <FormField label="Your Team" width="full" help="Sets your program and its real local beat writers. Lock it in before kickoff.">
            <TeamSelect teams={teams} value={team} onChange={(name) => onSelectTeam?.(name)} disabled={busy || teamBusy} />
          </FormField>
        )}
        <FormField label="Season Year" width="half">
          <TextInput type="number" inputMode="numeric" value={year} onValueChange={(v) => setYear(v.replace(/[^0-9]/g, ''))} />
        </FormField>
        <FormField label="Seed" width="half" help="Optional. Same seed + year reproduces the season.">
          <TextInput value={seed} placeholder="random" onValueChange={(v) => setSeed(v.replace(/[^0-9]/g, ''))} />
        </FormField>
      </div>
      <Button variant="accent" icon={<PlayIcon />} onClick={start} spinning={busy} disabled={busy || teamBusy}>
        {busy ? 'Building Season...' : 'Start New Season'}
      </Button>
    </Card>
  );
}
