import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { api } from '../../lib/api.js';
import Button from '../ui/Button.jsx';
import Callout from '../ui/Callout.jsx';
import EmptyState from '../ui/EmptyState.jsx';
import PanelCard from '../ui/PanelCard.jsx';
import SegmentedControl from '../ui/SegmentedControl.jsx';
import Skeleton from '../ui/Skeleton.jsx';
import StatusDot from '../ui/StatusDot.jsx';
import ToggleSwitch from '../ui/ToggleSwitch.jsx';
import RankingList from './RankingList.jsx';
import PollRankRow from './PollRankRow.jsx';
import PollRankingEditor from './PollRankingEditor.jsx';
import PollAlgorithmPicker from './PollAlgorithmPicker.jsx';

// The poll editor: hand any of the save's national polls to the user. Each
// poll (CFP committee, AP) runs in one of three modes: the game's own poll
// (read-only), the user's manual ranking (drag to reorder; only the head
// list is user-ordered, the rest keep the game's order), or a computer
// rating recomputed from the season's results. Config changes save
// immediately and the backend re-asserts the user's polls after every new
// game save (the auto-push watcher), so there is nothing to push weekly;
// the explicit push button is instant feedback plus the fallback when the
// watcher is unavailable. Data flows through /api/polls*; stories inject
// initialData and a previewFn instead.
const HEAD_SIZE = 25;

const MODE_OPTIONS = [
  { value: 'game', label: 'Game' },
  { value: 'manual', label: 'My Ranking' },
  { value: 'algorithm', label: 'Algorithm' },
];

export default function PollEditorPanel({
  toast,
  userTeam,
  initialData = null,
  initialPoll = 'cfp',
  onPollChange = null,
  previewFn = null,
}) {
  const [data, setData] = useState(initialData);
  const [error, setError] = useState(null);
  const [activePoll, setActivePoll] = useState(initialPoll);
  const [drafts, setDrafts] = useState({});       // poll -> manual entry objects
  const [previews, setPreviews] = useState({});   // `${poll}:${algo}` -> entries
  const [applying, setApplying] = useState(false);
  const saveTimer = useRef(null);
  const notify = toast || (() => {});

  const load = useCallback(async () => {
    try {
      setData(await api.polls());
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    if (!initialData) load();
    return () => clearTimeout(saveTimer.current);
  }, [initialData, load]);

  useEffect(() => {
    setActivePoll(initialPoll);
  }, [initialPoll]);

  const changePoll = useCallback((poll) => {
    setActivePoll(poll);
    onPollChange?.(poll);
  }, [onPollChange]);

  const cfg = data?.config;
  const pollCfg = cfg?.polls?.[activePoll];
  const entries = useMemo(() => data?.polls?.[activePoll] || [], [data, activePoll]);
  const hold = data?.holds?.[activePoll];
  const notice = data?.notices?.[activePoll];
  const pending = data?.pending?.[activePoll];
  const watcher = data?.autosync;

  // The manual draft for a poll: the saved manual names resolved against the
  // save's entries, or (first time) the current poll's head seeded in.
  const draft = useMemo(() => {
    if (drafts[activePoll]) return drafts[activePoll];
    const byName = Object.fromEntries(entries.map((e) => [e.team, e]));
    const names = (pollCfg?.manual?.length ? pollCfg.manual : entries.slice(0, HEAD_SIZE).map((e) => e.team));
    return names.map((n) => byName[n]).filter(Boolean);
  }, [drafts, activePoll, entries, pollCfg]);

  const saveConfig = useCallback(async (body, { quiet = false } = {}) => {
    try {
      const res = await api.savePollsConfig(body);
      setData((d) => (d ? { ...d, config: res.config } : d));
      if (res.applied?.written && !quiet) notify('Poll pushed to the dynasty file');
      // pending/current polls may have changed on disk; refresh quietly
      load();
    } catch (e) {
      notify('Could not save poll settings: ' + e.message);
    }
  }, [notify, load]);

  const setMode = (mode) => {
    const body = { polls: { [activePoll]: { mode } } };
    if (mode === 'manual' && !pollCfg?.manual?.length) {
      body.polls[activePoll].manual = draft.map((e) => e.team);
    }
    saveConfig(body);
  };

  const setAlgorithm = (algorithm) => {
    saveConfig({ polls: { [activePoll]: { algorithm } } });
  };

  const onReorder = (next) => {
    setDrafts((d) => ({ ...d, [activePoll]: next }));
    clearTimeout(saveTimer.current);
    const poll = activePoll;
    saveTimer.current = setTimeout(() => {
      saveConfig({ polls: { [poll]: { manual: next.map((e) => e.team) } } }, { quiet: true });
    }, 800);
  };

  const pushNow = async () => {
    setApplying(true);
    try {
      const res = await api.applyPolls();
      if (res.written) notify('Poll pushed to the dynasty file');
      else if (res.held && Object.keys(res.held).length) notify('Committee poll is held by the live playoff');
      else notify('The dynasty file already matches your poll');
      load();
    } catch (e) {
      notify('Push failed: ' + e.message);
    } finally {
      setApplying(false);
    }
  };

  // Algorithm preview (fetched lazily per poll+algorithm, cached).
  const algoId = pollCfg?.algorithm;
  const previewKey = `${activePoll}:${algoId}`;
  useEffect(() => {
    if (!data?.available || pollCfg?.mode !== 'algorithm' || !algoId) return undefined;
    if (previews[previewKey]) return undefined;
    let alive = true;
    const run = previewFn || ((algo, poll) => api.pollPreview(algo, poll));
    run(algoId, activePoll)
      .then((res) => { if (alive) setPreviews((p) => ({ ...p, [previewKey]: res.entries || [] })); })
      .catch(() => {});
    return () => { alive = false; };
  }, [data, pollCfg, algoId, activePoll, previewKey, previews, previewFn]);

  if (error) {
    return <Callout tone="warn" title="Could not load the polls">{error}</Callout>;
  }
  if (!data) {
    return <Skeleton height={420} />;
  }
  if (!data.available) {
    return <EmptyState>{data.reason || 'No CFB 27 save was found, so there are no polls to edit yet. Scan a dynasty first.'}</EmptyState>;
  }

  // jsonify sorts object keys, so order the segments explicitly: the
  // committee poll (the one the engine's selection reads) comes first
  const pollOptions = ['cfp', 'ap']
    .filter((p) => (data.poll_labels || {})[p])
    .map((p) => ({ value: p, label: data.poll_labels[p] }));
  const mode = pollCfg?.mode || 'game';
  const previewEntries = previews[previewKey] || null;
  const lastApplied = cfg?.last_applied;
  const algoName = (data.algorithms || []).find((a) => a.id === algoId)?.name;

  return (
    <div className="poll-editor">
      <div className="poll-editor-bar">
        <SegmentedControl options={pollOptions} value={activePoll} onChange={changePoll} />
        <div className="poll-editor-status">
          <span className="poll-editor-watch">
            <StatusDot tone={watcher?.active ? 'live' : 'idle'} pulse={!!watcher?.active} />
            {watcher?.active
              ? 'Auto-push armed: new game saves get your poll automatically'
              : 'Save watcher unavailable: push manually after each week'}
          </span>
          <ToggleSwitch
            checked={cfg?.auto_apply !== false}
            onChange={(v) => saveConfig({ auto_apply: v })}
            label="Auto-push"
          />
          <Button onClick={pushNow} disabled={applying || mode === 'game'}>
            {applying ? 'Pushing...' : pending ? 'Push to dynasty now' : 'Push again'}
          </Button>
        </div>
      </div>

      {hold && <Callout tone="warn" title="Committee poll temporarily held">{hold}</Callout>}
      {!hold && notice && (
        <Callout title="The game's playoff bracket is already set">{notice}</Callout>
      )}
      {lastApplied?.polls?.length > 0 && (
        <p className="poll-editor-last">
          Last pushed {lastApplied.at?.replace('T', ' ')} ({lastApplied.polls.join(', ').toUpperCase()}) into {lastApplied.save}
        </p>
      )}

      <div className="poll-layout">
        <div className="poll-controls">
          <PanelCard title="Who ranks this poll">
            <SegmentedControl options={MODE_OPTIONS} value={mode} onChange={setMode} />
            {mode === 'game' && (
              <p className="poll-mode-note">
                The game's engine keeps ranking this poll every week. Dynasty+ never touches it.
              </p>
            )}
            {mode === 'manual' && (
              <p className="poll-mode-note">
                Your hand ranking. Drag rows (or use the arrows) to reorder; it is re-applied
                to the dynasty file after every week you play.
              </p>
            )}
            {mode === 'algorithm' && (
              <p className="poll-mode-note">
                A computer poll: recomputed from this season's results after every game save
                and pushed into the dynasty automatically.
              </p>
            )}
          </PanelCard>
          {mode === 'algorithm' && (
            <PanelCard title="Ranking algorithm">
              <PollAlgorithmPicker
                algorithms={data.algorithms || []}
                value={algoId}
                onChange={setAlgorithm}
              />
            </PanelCard>
          )}
        </div>

        <div className="poll-list-pane">
          <PanelCard title={mode === 'algorithm' ? `${algoName || 'Algorithm'} preview` : (data.poll_labels || {})[activePoll] || 'Rankings'}>
            {mode === 'game' && (
              <RankingList teams={entries.slice(0, HEAD_SIZE)} userTeam={userTeam} variant="game" />
            )}
            {mode === 'manual' && (
              <PollRankingEditor
                entries={draft}
                onChange={onReorder}
                userTeam={userTeam}
                addOptions={entries.filter((e) => !draft.some((d) => d.team === e.team))}
              />
            )}
            {mode === 'algorithm' && (
              previewEntries === null ? <Skeleton height={320} /> : (
                <div>
                  {previewEntries.slice(0, HEAD_SIZE).map((e) => (
                    <PollRankRow key={e.team} entry={e} isUser={e.team === userTeam} />
                  ))}
                </div>
              )
            )}
          </PanelCard>
        </div>
      </div>
    </div>
  );
}
