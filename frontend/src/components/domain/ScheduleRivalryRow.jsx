import Button from '../ui/Button.jsx';
import Select from '../ui/Select.jsx';
import TeamHelmet from '../ui/TeamHelmet.jsx';
import TextInput from '../ui/TextInput.jsx';
import WeekSelect from '../ui/WeekSelect.jsx';

// One protected rivalry in the schedule rules: the two game-rendered helmets
// facing each other around a VS puck on the left, the rivalry's NAME (the
// game's own label for a known pair, editable to anything), then the week,
// the site, and the primary flag (a team's primary rival defaults to rivalry
// week and a team can only have one). Used for both conference rivalries and
// non-conference rivals. `teamOf` maps a team's full name to its setup entry
// ({school, abbr, espn_id, ...}); `defaultName` is the game's own name for
// the pair (shown until the user types their own). Presentational:
// onChange(updatedRivalry) / onRemove().
export default function ScheduleRivalryRow({
  rivalry,
  teamOf = () => null,
  weeks = null,
  defaultName = null,
  showPrimary = true,
  onChange,
  onRemove,
}) {
  const patch = (changes) => onChange?.({ ...rivalry, ...changes });
  const ta = teamOf(rivalry.a);
  const tb = teamOf(rivalry.b);
  const a = ta?.school || rivalry.a;
  const b = tb?.school || rivalry.b;
  return (
    <div className="sr-riv-row">
      <span className="sr-riv-pair" title={`${a} vs ${b}`}>
        <TeamHelmet espnId={ta?.espn_id} abbr={ta?.abbr} name={a} side="right" size={84} />
        <span className="sr-riv-vs">VS</span>
        <TeamHelmet espnId={tb?.espn_id} abbr={tb?.abbr} name={b} side="left" size={84} />
      </span>
      <span className="sr-riv-fields">
        <TextInput
          className="sr-riv-name"
          value={rivalry.name || ''}
          placeholder={defaultName || `${a} vs ${b}`}
          title="Rivalry name (shown on the protected game)"
          onValueChange={(name) => patch({ name: name || null })}
        />
        <span className="sr-riv-controls">
          <WeekSelect value={rivalry.week} onChange={(week) => patch({ week })} weeks={weeks} />
          <Select
            options={[
              { value: 'rotate', label: 'Alternate home and away' },
              { value: 'home_a', label: `Always at ${a}` },
              { value: 'home_b', label: `Always at ${b}` },
            ]}
            value={rivalry.location || 'rotate'}
            onValueChange={(location) => patch({ location })}
          />
          {showPrimary && (
            <button
              type="button"
              className={`sr-riv-primary${rivalry.primary ? ' on' : ''}`}
              title="A primary rival is scheduled in rivalry week unless another week is picked"
              onClick={() => patch({ primary: !rivalry.primary })}
            >
              {rivalry.primary ? 'Primary rival' : 'Set primary'}
            </button>
          )}
          <Button onClick={onRemove}>Remove</Button>
        </span>
      </span>
    </div>
  );
}
