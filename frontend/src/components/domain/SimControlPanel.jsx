import SectionTitle from '../ui/SectionTitle.jsx';
import Button from '../ui/Button.jsx';
import * as Icons from '../ui/icons.jsx';
import ScoreOverrideForm from './ScoreOverrideForm.jsx';

// The season driver's "up next" control surface: the upcoming user game with an
// optional score override, and the controls that play the week. Two-step flow:
// "Simulate Game" plays the week but stays on it (so the post-game press
// conference can run in Dynasty+ and feed this week's coverage), then "Advance"
// moves to the next week. `simmed` flips the panel from pre-game to post-game.
export default function SimControlPanel({
  week,
  userGame,
  simmed = false,
  override = { enabled: false, value: { user_score: '', opp_score: '' } },
  onToggleOverride,
  onChangeOverride,
  onSimulateGame,
  onAdvance,
  busy = false,
}) {
  return (
    <div className="debug-next">
      <SectionTitle>{simmed ? `Week ${week}, Final` : `Up Next, Week ${week}`}</SectionTitle>
      {userGame && !simmed && (
        <ScoreOverrideForm
          team={userGame.team}
          opponent={userGame.opponent}
          home={userGame.home}
          week={userGame.week}
          enabled={override.enabled}
          value={override.value}
          onToggle={onToggleOverride}
          onChange={onChangeOverride}
        />
      )}
      {simmed ? (
        <>
          <p style={{ color: 'var(--chalk-3)', fontSize: 13, margin: '0 0 10px' }}>
            Game played. Answer the post-game press conference in Dynasty+ (it can run now while you
            stay on this week), then advance when you are ready.
          </p>
          <Button variant="accent" icon={<Icons.PlayIcon />} onClick={onAdvance} spinning={busy} disabled={busy}>
            {busy ? 'Advancing...' : `Advance to Week ${week + 1}`}
          </Button>
        </>
      ) : (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button variant="accent" icon={<Icons.PlayIcon />} onClick={onSimulateGame} spinning={busy} disabled={busy}>
            {busy ? 'Simulating...' : 'Simulate Game'}
          </Button>
          <Button variant="action" onClick={onAdvance} disabled={busy}>
            Simulate &amp; Advance
          </Button>
        </div>
      )}
    </div>
  );
}
