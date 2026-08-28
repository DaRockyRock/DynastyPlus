import { useApp } from '../context/AppContext.jsx';
import { ScheduleRulesEditor } from '../components/index.js';

// The Schedule tab: the custom schedule generator. Per-conference
// scheduling rules, protected conference and non-conference rivalries with
// weeks and locations, the feasibility report, and the generate / apply flow
// that rewrites the active save's regular season in place. Everything flows
// through /api/schedule/*.
export default function SchedulePage() {
  const { toast } = useApp();
  return (
    <div className="schedule-tool">
      <ScheduleRulesEditor embedded toast={toast} />
    </div>
  );
}
