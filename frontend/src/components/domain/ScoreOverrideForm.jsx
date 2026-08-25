import Card from '../ui/Card.jsx';
import TeamLogo from '../ui/TeamLogo.jsx';
import TextInput from '../ui/TextInput.jsx';

// Set your own result before locking the week (you "play" the game in CFB 27;
// here you can dictate the score). When the toggle is off the engine sims your
// game like everyone else. `value` is { user_score, opp_score }.
export default function ScoreOverrideForm({ team, opponent, home, week, enabled, value, onToggle, onChange }) {
  const v = value || { user_score: '', opp_score: '' };
  const set = (key) => (val) => onChange?.({ ...v, [key]: val.replace(/[^0-9]/g, '') });

  return (
    <Card className="override-card">
      <label className="ov-toggle">
        <input type="checkbox" checked={!!enabled} onChange={(e) => onToggle?.(e.target.checked)} />
        <span>Set my result for Week {week}</span>
      </label>
      <div className={['ov-body', enabled ? '' : 'is-disabled'].filter(Boolean).join(' ')}>
        <div className="ov-side">
          <TeamLogo espnId={team.espn_id} abbr={team.abbr} name={team.name} size={30} />
          <span className="ov-abbr">{team.abbr}</span>
          <TextInput type="number" min="0" inputMode="numeric" className="ov-score"
                     value={v.user_score} onValueChange={set('user_score')} disabled={!enabled} />
        </div>
        <span className="ov-at">{home ? 'vs' : 'at'}</span>
        <div className="ov-side">
          <TextInput type="number" min="0" inputMode="numeric" className="ov-score"
                     value={v.opp_score} onValueChange={set('opp_score')} disabled={!enabled} />
          <span className="ov-abbr">{opponent.abbr}</span>
          <TeamLogo espnId={opponent.espn_id} abbr={opponent.abbr} name={opponent.name} size={30} />
        </div>
      </div>
    </Card>
  );
}
