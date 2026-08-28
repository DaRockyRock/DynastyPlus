import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../../lib/api.js';
import Button from '../ui/Button.jsx';
import Callout from '../ui/Callout.jsx';
import Chip from '../ui/Chip.jsx';
import EmptyState from '../ui/EmptyState.jsx';
import SegmentedControl from '../ui/SegmentedControl.jsx';
import Skeleton from '../ui/Skeleton.jsx';
import PollSwitch from './PollSwitch.jsx';
import RankCardGrid from './RankCardGrid.jsx';
import TeamResumeModal from './TeamResumeModal.jsx';
import WeekScoreboardPanel from './WeekScoreboardPanel.jsx';
import PollEditorPanel from './PollEditorPanel.jsx';

// The rankings hub: the save's national polls as a branded
// card grid, click-through team resumes with side-by-side comparison, the
// league scoreboard, and the poll editor, one surface. Data flows through
// /api/polls and /api/rankings/*; stories inject initialData, scoreboardData,
// and a resumeFn instead.
const VIEWS = [
  { value: 'rankings', label: 'Rankings' },
  { value: 'scoreboard', label: 'Scoreboard' },
  { value: 'editor', label: 'Poll Editor' },
];

const MODE_CHIP = {
  game: 'Engine ranked',
  manual: 'Your ranking',
  algorithm: 'Computer poll',
};

export default function RankingsHubPanel({
  toast, userTeam, initialData = null, scoreboardData = null, resumeFn = null,
}) {
  const [data, setData] = useState(initialData);
  const [error, setError] = useState(null);
  const [view, setView] = useState('rankings');
  const [activePoll, setActivePoll] = useState('cfp');
  const [showAll, setShowAll] = useState(false);
  const [scoreboard, setScoreboard] = useState(scoreboardData);
  const [openRow, setOpenRow] = useState(null);          // resume subject
  const [compareWith, setCompareWith] = useState(null);  // pinned opponent
  const [pins, setPins] = useState([]);                  // compare pins (max 2)
  const [resumes, setResumes] = useState({});            // row -> payload
  const [resumeLoading, setResumeLoading] = useState(false);
  const cacheRef = useRef(resumes);
  cacheRef.current = resumes;

  const fetchResume = useCallback(async (row) => {
    if (cacheRef.current[row]) return cacheRef.current[row];
    const run = resumeFn || api.teamResume;
    const payload = await run(row);
    setResumes((r) => ({ ...r, [row]: payload }));
    return payload;
  }, [resumeFn]);

  const loadPolls = useCallback(async () => {
    try {
      setData(await api.polls());
      setError(null);
      // a pushed poll can change every rank on screen; drop stale resumes
      setResumes({});
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    if (!initialData) loadPolls();
  }, [initialData, loadPolls]);

  // the scoreboard loads lazily, the first time its view opens
  useEffect(() => {
    if (view !== 'scoreboard' || scoreboard) return;
    api.rankingsScoreboard().then(setScoreboard).catch((e) => setError(e.message));
  }, [view, scoreboard]);

  // leaving the editor re-reads the polls (a push may have rewritten them)
  const changeView = (v) => {
    if (view === 'editor' && v !== 'editor' && !initialData) loadPolls();
    setView(v);
  };

  const openResume = async (entry) => {
    setOpenRow(entry.row);
    setCompareWith(null);
    setResumeLoading(true);
    try {
      await fetchResume(entry.row);
    } catch (e) {
      setError(e.message);
    } finally {
      setResumeLoading(false);
    }
  };

  const togglePin = (entry) => {
    setPins((cur) => {
      if (cur.includes(entry.row)) return cur.filter((r) => r !== entry.row);
      const next = [...cur, entry.row].slice(-2);
      if (next.length === 2) {
        // the second pin opens the tape immediately
        setCompareWith(next[1]);
        setOpenRow(next[0]);
        setResumeLoading(true);
        fetchResume(next[0])
          .catch(() => {})
          .finally(() => setResumeLoading(false));
        return [];
      }
      return next;
    });
  };

  if (error && !data) {
    return <Callout tone="warn" title="Could not load the rankings">{error}</Callout>;
  }
  if (!data) return <Skeleton height={480} />;
  if (!data.available) {
    return <EmptyState>{data.reason || 'No CFB 27 save was found, so there are no rankings yet. Scan a dynasty first.'}</EmptyState>;
  }

  // the effective ordering reflects the user's edited poll (manual head /
  // algorithm) right away; fall back to the save's current order
  const entries = data.effective?.[activePoll] || data.polls?.[activePoll] || [];
  const mode = data.config?.polls?.[activePoll]?.mode || 'game';
  const algoName = mode === 'algorithm'
    ? (data.algorithms || []).find((a) => a.id === data.config?.polls?.[activePoll]?.algorithm)?.name
    : null;

  return (
    <div className="rankings-hub">
      <div className="rh-bar">
        <PollSwitch
          value={activePoll}
          onChange={setActivePoll}
          polls={['cfp', 'ap'].filter((p) => (data.poll_labels || {})[p])}
          labels={data.poll_labels}
        />
        <div className="rh-bar-side">
          {view === 'rankings' && (
            <Chip category={algoName || MODE_CHIP[mode]} accent={mode === 'game' ? 'var(--national)' : 'var(--cfp)'} />
          )}
          <SegmentedControl options={VIEWS} value={view} onChange={changeView} />
        </div>
      </div>

      {view === 'rankings' && (
        <>
          <RankCardGrid
            entries={entries}
            max={showAll ? null : 25}
            userTeam={userTeam}
            comparedRows={pins}
            onOpen={openResume}
            onCompare={togglePin}
          />
          {entries.length > 25 && (
            <div className="rh-foot">
              <Button onClick={() => setShowAll((s) => !s)}>
                {showAll ? 'Show the Top 25' : `Show the full field (${entries.length})`}
              </Button>
            </div>
          )}
        </>
      )}

      {view === 'scoreboard' && (
        scoreboard ? <WeekScoreboardPanel data={scoreboard} userTeam={userTeam} /> : <Skeleton height={420} />
      )}

      {view === 'editor' && (
        <PollEditorPanel
          toast={toast}
          userTeam={userTeam}
          initialData={data}
          initialPoll={activePoll}
          onPollChange={setActivePoll}
        />
      )}

      <TeamResumeModal
        open={openRow != null}
        onClose={() => { setOpenRow(null); setCompareWith(null); }}
        resume={openRow != null ? resumes[openRow] : null}
        loading={resumeLoading}
        entries={entries}
        loadResume={fetchResume}
        initialCompareRow={compareWith}
      />
    </div>
  );
}
