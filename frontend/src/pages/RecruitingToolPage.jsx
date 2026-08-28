import { useApp } from '../context/AppContext.jsx';
import { useRecruitingTool } from '../hooks/useRecruitingTool.js';
import {
  GameScreen, RecruitingAutomationPanel, Skeleton, EmptyState,
} from '../components/index.js';

export default function RecruitingToolPage() {
  const { pointer } = useApp();
  const { data, loading, busy, error, setEnabled, apply } = useRecruitingTool();
  return (
    <GameScreen
      week={`Week ${pointer.week}, ${pointer.year}`}
      heroTitle="Recruiting Competition"
      heroSub="Keep scholarship offers and CPU attention aligned with the national class."
    >
      {loading ? <Skeleton height={360} />
        : error ? <EmptyState>Could not read recruiting data: {error}</EmptyState>
        : !data?.available ? <EmptyState>{data?.reason || 'Recruiting data is not available in this save.'}</EmptyState>
        : (
          <RecruitingAutomationPanel
            data={data}
            busy={busy}
            onToggle={setEnabled}
            onApply={apply}
          />
        )}
    </GameScreen>
  );
}
