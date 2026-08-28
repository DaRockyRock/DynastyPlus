import { useEffect, useState } from 'react';
import { api } from '../lib/api.js';
import { useApp } from '../context/AppContext.jsx';
import { PlayoffBracket, PlayoffGuide, PlayoffLiveStatus, PlayoffAutomationToggle, PlayoffOffState, PanelCard, DataUnavailableNotice } from '../components/index.js';

// The LIVE custom playoff over the real CFB 27 save: a
// projected field during the regular season (from the save's own rankings,
// records, and rivalry results), the frozen bracket once the CCGs are
// official, live results as rounds complete, and past champions from the
// dynasty's playoff history. Polling /api/playoff/live doubles as the
// automation heartbeat: every poll pushes newly-decided matchups into the
// save (the folder watcher does the same the moment the game writes a save).
// Polled tightly so the walkthrough guide's current-step cursor tracks the
// dynasty save (game played, week advanced, save updated) in near real time.
const POLL_MS = 10_000;

export default function PlayoffLivePage() {
  const { dynasty, toast } = useApp();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [applying, setApplying] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [openYear, setOpenYear] = useState(null);

  useEffect(() => {
    let alive = true;
    const load = () => api.playoffLive()
      .then((res) => { if (alive) { setData(res); setError(null); } })
      .catch((e) => { if (alive) setError(e.message); });
    load();
    const t = setInterval(load, POLL_MS);
    return () => { alive = false; clearInterval(t); };
  }, []);

  // the "update dynasty file" button: writes pending matchups / a due rewind
  // into the save; pressed while the dynasty is closed in CFB 27
  const apply = async () => {
    setApplying(true);
    try {
      const res = await api.playoffApply();
      setData(res);
      toast?.(res.save_written
        ? 'Dynasty file updated. Load the dynasty in CFB 27 to play the new games.'
        : 'Nothing to write; the save is already up to date.');
    } catch (e) {
      toast?.('Update failed: ' + e.message);
    } finally {
      setApplying(false);
    }
  };

  // Turn the custom bracket automation on/off. Off (the default) hands the
  // postseason back to CFB 27's native 12-team playoff: no update prompts.
  const toggleEnabled = async (next) => {
    setToggling(true);
    try {
      await api.setPlayoffConfig({ enabled: next });
      const res = await api.playoffLive();
      setData(res);
      setError(null);
      toast?.(next
        ? 'Custom playoff bracket on'
        : 'Custom playoff bracket off. CFB 27 runs its native playoff.');
    } catch (e) {
      toast?.('Could not change the setting: ' + e.message);
    } finally {
      setToggling(false);
    }
  };

  const userTeamId = dynasty?.team?.espn_id;
  const bracket = data?.bracket;
  // `enabled` is undefined only until the first load lands; treat that as "on"
  // so an in-progress bracket never flashes the off state while loading.
  const off = data ? data.enabled === false : false;

  // Off: the game owns its postseason, so the whole page collapses to the
  // off-state hero, the switch front and center. Nothing else renders.
  if (off) {
    return (
      <div className="page playoff-live">
        {error && <DataUnavailableNotice reason={error} />}
        <PlayoffOffState onEnable={() => toggleEnabled(true)} busy={toggling} />
      </div>
    );
  }

  return (
    <div className="page playoff-live">
      {error && <DataUnavailableNotice reason={error} />}
      {/* the master on/off switch: off hands the postseason to
          the game's native 12-team playoff and silences the update prompts */}
      {data && (
        <PlayoffAutomationToggle
          enabled
          onChange={toggleEnabled}
          busy={toggling}
        />
      )}
      {/* the walkthrough: every phase of the playoff as a box, with the
          user's current step highlighted, tracking the save via polling */}
      {data?.guide && <PlayoffGuide guide={data.guide} />}
      {/* quiet action banner: update-save button when a wave is pending,
          load-your-dynasty confirmation after an update, format problems */}
      {data && (
        <PlayoffLiveStatus
          needsWrite={data.needs_write}
          awaitingReload={data.awaiting_reload}
          applying={applying}
          onApply={apply}
          problems={data.problems}
        />
      )}
      {bracket && <PlayoffBracket bracket={bracket} userTeamId={userTeamId} />}
      {!!(data?.history || []).length && (
        <PanelCard title="Playoff History">
          {/* every completed season's FULL bracket is archived here (every
              matchup, score, and site): the app's record is the source of
              truth, because oversized formats recycle save records and the
              game's own history only keeps the last occupant of each slot */}
          <div className="plv-history">
            {data.history.map((h) => (
              <div key={h.year}>
                <button
                  type="button"
                  className={`plv-history-row plv-history-toggle${openYear === h.year ? ' open' : ''}`}
                  onClick={() => setOpenYear(openYear === h.year ? null : h.year)}
                >
                  <span className="plv-history-year">{h.year}</span>
                  <span className="plv-history-champ">{h.champion?.team || 'Unknown champion'}</span>
                  <span className="plv-history-format">
                    {h.format_teams}-team field {openYear === h.year ? '(hide bracket)' : '(view bracket)'}
                  </span>
                </button>
                {openYear === h.year && h.bracket && (
                  <div className="plv-history-bracket">
                    <PlayoffBracket bracket={h.bracket} userTeamId={userTeamId} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </PanelCard>
      )}
    </div>
  );
}
