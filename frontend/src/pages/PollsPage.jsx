import { useApp } from '../context/AppContext.jsx';
import { GameScreen, RankingsHubPanel } from '../components/index.js';

// The Rankings tab: the save's national polls as a branded
// card grid with click-through team resumes, side-by-side comparison for
// playoff edge cases, the league scoreboard, and the poll editor (manual or
// computer rankings, auto-pushed into the dynasty file after every week).
export default function PollsPage() {
  const { dynasty, toast } = useApp();
  return (
    <GameScreen>
      <RankingsHubPanel toast={toast} userTeam={dynasty?.team?.name} />
    </GameScreen>
  );
}
