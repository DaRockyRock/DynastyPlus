import { useMemo, useState } from 'react';
import PanelCard from '../ui/PanelCard.jsx';
import FormField from '../ui/FormField.jsx';
import Select from '../ui/Select.jsx';
import Button from '../ui/Button.jsx';
import WeekSelect from '../ui/WeekSelect.jsx';
import ScheduleRivalryRow from './ScheduleRivalryRow.jsx';

// Protected NON-conference rivals, league-wide. A pair is symmetric (setting
// Army vs Navy protects it for both sides), every team holds at most
// `maxPerTeam` pairs, a pair can be pinned to a WEEK right when it is added,
// and a team's number 1 rival lands in rivalry week unless another week is
// picked. `teams` is every FBS team (grouped into conference optgroups);
// `gameRivalries` is the save's own named rivalry table (a known pair takes
// its real name automatically); `conferenceNames` are the conferences that
// have their own rules tab (so an in-conference pair can be redirected there);
// `value` is the rules list [{a, b, rank, week, location, name}].
// Presentational: onChange(newList).
export default function NonConRivalsCard({
  teams = [], value = [], weeks, maxPerTeam = 2, gameRivalries = [],
  conferenceNames = [], onChange,
}) {
  const [a, setA] = useState('');
  const [b, setB] = useState('');
  const [rank, setRank] = useState('1');
  const [week, setWeek] = useState(null);

  const byName = useMemo(() => Object.fromEntries(teams.map((t) => [t.name, t])), [teams]);
  const teamOf = (name) => byName[name] || null;
  const schoolOf = (name) => byName[name]?.school || name;
  const gameNameOf = (x, y) => gameRivalries.find(
    (r) => (r.a === x && r.b === y) || (r.a === y && r.b === x))?.name || null;
  const counts = useMemo(() => {
    const c = {};
    value.forEach((r) => {
      c[r.a] = (c[r.a] || 0) + 1;
      c[r.b] = (c[r.b] || 0) + 1;
    });
    return c;
  }, [value]);

  const groups = useMemo(() => {
    const conf = {};
    teams.forEach((t) => {
      const key = t.conference || 'Independents';
      (conf[key] = conf[key] || []).push(t);
    });
    return Object.entries(conf).map(([label, list]) => ({
      label,
      options: list.map((t) => ({ value: t.name, label: t.school })),
    }));
  }, [teams]);

  // Two teams only need redirecting to a conference tab when they share a
  // conference that HAS one. Independents carry their pool name as a
  // "conference" in the save but have no tab, so two independents must be
  // protectable right here (matching the backend's independent_pools rule).
  const tabbed = useMemo(() => new Set(conferenceNames), [conferenceNames]);
  const sameConf = a && b && byName[a]?.conference
    && byName[a]?.conference === byName[b]?.conference
    && tabbed.has(byName[a]?.conference);
  const overCap = [a, b].some((n) => n && (counts[n] || 0) >= maxPerTeam);
  const duplicate = value.some((r) => (r.a === a && r.b === b) || (r.a === b && r.b === a));
  const blocked = !a || !b || a === b || sameConf || overCap || duplicate;
  let note = `Rivals are set on both teams at once; each team can protect up to ${maxPerTeam}. A number 1 rival plays in rivalry week unless you pick a week.`;
  if (sameConf) note = `${schoolOf(a)} and ${schoolOf(b)} share a conference; protect that game in the conference's own rules.`;
  else if (overCap) note = `A team already holds ${maxPerTeam} protected rivals; remove one first.`;
  else if (duplicate) note = 'That pair is already protected.';

  const add = () => {
    if (blocked) return;
    onChange?.([...value, {
      a, b, rank: Number(rank), week, location: 'rotate', name: gameNameOf(a, b),
    }]);
    setA('');
    setB('');
    setRank('1');
    setWeek(null);
  };

  return (
    <PanelCard title="Non-Conference Rivals" right={`${value.length} protected`}>
      <div className="sr-nc-note">{note}</div>
      <div className="sr-riv-list">
        {value.length === 0 && (
          <div className="sr-riv-empty">No protected non-conference rivals yet. Army vs Navy, Notre Dame vs USC, Florida vs Florida State...</div>
        )}
        {value.map((r, i) => (
          <ScheduleRivalryRow
            key={`${r.a}-${r.b}-${i}`}
            rivalry={{ ...r, primary: r.rank === 1 }}
            teamOf={teamOf}
            defaultName={gameNameOf(r.a, r.b)}
            weeks={weeks}
            onChange={(nr) => onChange?.(value.map((x, j) => (
              j === i
                ? { a: nr.a, b: nr.b, week: nr.week, location: nr.location, name: nr.name, rank: nr.primary ? 1 : 2 }
                : x
            )))}
            onRemove={() => onChange?.(value.filter((_, j) => j !== i))}
          />
        ))}
      </div>
      <div className="sr-riv-add">
        <FormField label="Team">
          <Select options={[{ value: '', label: 'Select team' }]} groups={groups} value={a} onValueChange={setA} />
        </FormField>
        <FormField label="Rival">
          <Select options={[{ value: '', label: 'Select team' }]} groups={groups} value={b} onValueChange={setB} />
        </FormField>
        <FormField label="Priority">
          <Select
            options={[
              { value: '1', label: 'Number 1 rival (rivalry week)' },
              { value: '2', label: 'Number 2 rival' },
            ]}
            value={rank}
            onValueChange={setRank}
          />
        </FormField>
        <FormField label="Week">
          <WeekSelect value={week} onChange={setWeek} weeks={weeks} />
        </FormField>
        <Button variant="accent" onClick={add} disabled={blocked}>Protect Rivals</Button>
      </div>
    </PanelCard>
  );
}
