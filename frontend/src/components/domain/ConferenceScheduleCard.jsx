import { useState } from 'react';
import PanelCard from '../ui/PanelCard.jsx';
import NumberStepper from '../ui/NumberStepper.jsx';
import ToggleSwitch from '../ui/ToggleSwitch.jsx';
import FormField from '../ui/FormField.jsx';
import Select from '../ui/Select.jsx';
import Button from '../ui/Button.jsx';
import ConferenceLogo from '../ui/ConferenceLogo.jsx';
import ScheduleRivalryRow from './ScheduleRivalryRow.jsx';

// One conference's scheduling rules: how many conference games every member
// plays, an optional full division round robin, and the protected rivalries
// (each rendered as a helmet matchup with the rivalry's name, a week, and a
// location). `conference` comes from /api/schedule/setup; `gameRivalries` is
// the save's own named rivalry table (a new protected pair takes its real
// name automatically); `value` is the editable slice {games,
// round_robin_divisions, rivalries}. Presentational: onChange(newValue).
export default function ConferenceScheduleCard({ conference, value, weeks, gameRivalries = [], onChange }) {
  const teams = conference?.teams || [];
  const v = value || {};
  const rivalries = v.rivalries || [];
  const [a, setA] = useState('');
  const [b, setB] = useState('');

  const patch = (changes) => onChange?.({ ...v, ...changes });
  const teamOf = (name) => teams.find((t) => t.name === name) || null;
  const gameNameOf = (x, y) => gameRivalries.find(
    (r) => (r.a === x && r.b === y) || (r.a === y && r.b === x))?.name || null;
  const opts = (excluded) => [
    { value: '', label: 'Select team' },
    ...teams.filter((t) => t.name !== excluded)
      .map((t) => ({ value: t.name, label: t.school })),
  ];

  const observed = Object.entries(conference?.observed_games || {})
    .map(([k, n]) => `${n} at ${k}`).join(', ');
  const parityBad = (teams.length * (v.games || 0)) % 2 === 1;

  const add = () => {
    if (!a || !b || a === b) return;
    patch({
      rivalries: [...rivalries, {
        a, b, week: null, location: 'rotate', primary: false, name: gameNameOf(a, b),
      }],
    });
    setA('');
    setB('');
  };

  return (
    <PanelCard
      title={(
        <span className="sr-conf-title">
          <ConferenceLogo name={conference?.canonical || conference?.name} size={22} plate={false} />
          {conference?.name || 'Conference'}
        </span>
      )}
      right={`${teams.length} teams`}
    >
      <div className="sr-row">
        <span className="sr-row-label">
          Conference games per team
          <span className="sr-row-sub">
            {parityBad
              ? `${teams.length} teams times ${v.games} games does not pair up; use an even total`
              : `The save's own schedule plays ${observed || 'none'}`}
          </span>
        </span>
        <NumberStepper
          value={v.games || 0}
          min={1}
          max={conference?.max_games || Math.max(1, teams.length - 1)}
          onChange={(games) => patch({ games })}
        />
      </div>
      {(conference?.divisions?.length || 0) > 1 && (
        <div className="sr-row">
          <span className="sr-row-label">
            Full division round robin
            <span className="sr-row-sub">Every team plays its whole division; the rest are crossover games</span>
          </span>
          <ToggleSwitch
            checked={!!v.round_robin_divisions}
            onChange={(round_robin_divisions) => patch({ round_robin_divisions })}
          />
        </div>
      )}
      <div className="sr-riv-list">
        {rivalries.length === 0 && (
          <div className="sr-riv-empty">No protected conference rivalries. Every matchup is up to the generator.</div>
        )}
        {rivalries.map((r, i) => (
          <ScheduleRivalryRow
            key={`${r.a}-${r.b}-${i}`}
            rivalry={r}
            teamOf={teamOf}
            defaultName={gameNameOf(r.a, r.b)}
            weeks={weeks}
            onChange={(nr) => patch({ rivalries: rivalries.map((x, j) => (j === i ? nr : x)) })}
            onRemove={() => patch({ rivalries: rivalries.filter((_, j) => j !== i) })}
          />
        ))}
      </div>
      <div className="sr-riv-add">
        <FormField label="Team">
          <Select options={opts(b)} value={a} onValueChange={setA} />
        </FormField>
        <FormField label="Protected rival">
          <Select options={opts(a)} value={b} onValueChange={setB} />
        </FormField>
        <Button variant="accent" onClick={add} disabled={!a || !b || a === b}>Protect Rivalry</Button>
      </div>
    </PanelCard>
  );
}
