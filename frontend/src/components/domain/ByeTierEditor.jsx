import NumberStepper from '../ui/NumberStepper.jsx';

// Editor for the format's bye tiers. Three tiers cover every sane bracket:
// a single bye enters one round late, a double bye two, a triple bye three.
// Emits only tiers with at least one team, the shape backend/playoff.py stores:
// [{rounds, teams}].
const TIERS = [
  { rounds: 1, label: 'Single byes', sub: 'Skip the opening round' },
  { rounds: 2, label: 'Double byes', sub: 'Skip the first two rounds' },
  { rounds: 3, label: 'Triple byes', sub: 'Skip the first three rounds' },
];

export default function ByeTierEditor({ tiers = [], onChange, maxTeams = 128 }) {
  const byRounds = {};
  tiers.forEach((t) => { byRounds[t.rounds] = t.teams; });

  const set = (rounds, teams) => {
    const next = { ...byRounds, [rounds]: teams };
    onChange?.(
      Object.entries(next)
        .filter(([, n]) => n > 0)
        .map(([r, n]) => ({ rounds: Number(r), teams: n })),
    );
  };

  return (
    <div className="pfe-stack">
      {TIERS.map((t) => (
        <div className="pfe-tier-row" key={t.rounds}>
          <span className="pfe-tier-label">
            {t.label}
            <span className="pfe-row-sub">{t.sub}</span>
          </span>
          <NumberStepper
            value={byRounds[t.rounds] || 0}
            min={0}
            max={maxTeams}
            onChange={(v) => set(t.rounds, v)}
            suffix="teams"
          />
        </div>
      ))}
    </div>
  );
}
