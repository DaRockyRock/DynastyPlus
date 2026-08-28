import SegmentedControl from '../ui/SegmentedControl.jsx';
import Select from '../ui/Select.jsx';
import TextInput from '../ui/TextInput.jsx';
import StadiumSelect from './StadiumSelect.jsx';

// Site configuration for ONE playoff round: play at the higher seed's stadium,
// tie each game to a bowl, or send the round to a neutral site. `games` is the
// round's games from the live preview (so bowl pickers show what the engine
// resolved); edits write into the round's site config
// ({mode, bowls, venue, city, games:[{bowl}...]}, see backend/playoff.py).
const MODES = [
  { value: 'higher_seed', label: 'Higher Seed' },
  { value: 'bowls', label: 'Bowls' },
  { value: 'neutral', label: 'Neutral' },
];

export default function RoundSiteEditor({ name, games = [], config = {}, bowls = [], stadiums = [], onChange }) {
  const cfg = { mode: 'bowls', bowls: [], games: [], ...config };
  const update = (patch) => onChange?.({ ...cfg, ...patch });

  const setGameBowl = (i, key) => {
    const next = [...(cfg.games || [])];
    while (next.length <= i) next.push(null);
    next[i] = { ...(next[i] || {}), bowl: key || null };
    update({ games: next });
  };

  const bowlOptions = bowls.map((b) => ({ value: b.key, label: b.name }));

  return (
    <div className="pfe-stack">
      <div className="pfe-row">
        <span className="pfe-row-label">{name}</span>
        <SegmentedControl options={MODES} value={cfg.mode} onChange={(mode) => update({ mode })} />
      </div>
      {cfg.mode === 'bowls' && games.map((g, i) => (
        <div className="pfe-game-row" key={g.id || i}>
          <span className="pfe-game-num">Game {i + 1}</span>
          <Select
            options={bowlOptions}
            value={cfg.games?.[i]?.bowl ?? g.site?.bowl?.key ?? ''}
            onValueChange={(v) => setGameBowl(i, v)}
          />
        </div>
      ))}
      {cfg.mode === 'neutral' && (stadiums.length ? (
        // The game's real stadium table: picking one stores the save-stable
        // stadium id (what the writer pushes into the save) plus its labels.
        <div className="pfe-game-row">
          <StadiumSelect
            stadiums={stadiums}
            value={cfg.stadium}
            onPick={(s) => update(s
              ? { stadium: s.index, venue: s.name, city: s.city || '' }
              : { stadium: null, venue: '', city: '' })}
          />
        </div>
      ) : (
        // No real save readable (mock/dev): free-text labels only.
        <div className="pfe-game-row">
          <TextInput placeholder="Venue" value={cfg.venue || ''} onValueChange={(v) => update({ venue: v })} />
          <TextInput placeholder="City" value={cfg.city || ''} onValueChange={(v) => update({ city: v })} />
        </div>
      ))}
    </div>
  );
}
