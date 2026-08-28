import { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '../../lib/api.js';
import Button from '../ui/Button.jsx';
import Callout from '../ui/Callout.jsx';
import PanelCard from '../ui/PanelCard.jsx';
import ConferenceScheduleCard from './ConferenceScheduleCard.jsx';
import NonConRivalsCard from './NonConRivalsCard.jsx';
import ScheduleConferenceTabs, { NONCON_TAB } from './ScheduleConferenceTabs.jsx';
import ScheduleFeasibilityPanel from './ScheduleFeasibilityPanel.jsx';
import SchedulePreview from './SchedulePreview.jsx';

// The custom schedule studio (an editor tool, shipped in BOTH apps): per
// conference rules (game counts, protected rivalries with weeks and sites,
// division round robins) plus league-wide protected non-conference rivals,
// a live feasibility report with concrete fixes, and the generate / shuffle /
// apply flow that rewrites the active save's regular season in place. Data
// flows through /api/schedule/*; stories inject initialData and stub api fns.
const rulesOf = (state) => ({
  conferences: Object.fromEntries((state?.conferences || []).map((c) => [c.name, {
    games: c.games,
    round_robin_divisions: !!c.round_robin_divisions,
    rivalries: c.rivalries || [],
  }])),
  nonconference: state?.nonconference || [],
});
const eq = (x, y) => JSON.stringify(x) === JSON.stringify(y);

export default function ScheduleRulesEditor({ embedded = false, toast, initialData = null, apiFns = null }) {
  const fns = apiFns || {
    load: api.scheduleSetup,
    save: api.saveScheduleSetup,
    reset: api.resetScheduleSetup,
    generate: api.generateSchedule,
    apply: api.applySchedule,
  };
  const [state, setState] = useState(initialData);
  const [draft, setDraft] = useState(initialData ? rulesOf(initialData) : null);
  const [preview, setPreview] = useState(initialData?.plan_preview || null);
  const [genErrors, setGenErrors] = useState([]);
  const [busy, setBusy] = useState(null);   // 'save' | 'generate' | 'apply'
  const [error, setError] = useState(null);
  const [tab, setTab] = useState(null);     // conference name | NONCON_TAB
  const notify = toast || (() => {});

  useEffect(() => {
    if (state) return undefined;
    let alive = true;
    fns.load()
      .then((res) => {
        if (!alive) return;
        setState(res);
        setDraft(rulesOf(res));
        setPreview(res.plan_preview || null);
      })
      .catch((e) => { if (alive) setError(e.message); });
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const dirty = useMemo(() => state && draft && !eq(draft, rulesOf(state)), [state, draft]);
  const allTeams = useMemo(() => {
    const teams = (state?.conferences || []).flatMap((c) => c.teams);
    return [...teams, ...(state?.independents || [])];
  }, [state]);

  const adopt = useCallback((res) => {
    setState(res);
    setDraft(rulesOf(res));
    setPreview(res.plan_preview || null);
    setGenErrors([]);
  }, []);

  const save = async () => {
    setBusy('save');
    try {
      adopt(await fns.save(draft));
      notify('Schedule rules saved');
    } catch (e) {
      notify('Save failed: ' + e.message);
    } finally {
      setBusy(null);
    }
  };

  const reset = async () => {
    setBusy('save');
    try {
      adopt(await fns.reset());
      notify('Schedule rules reset to the save');
    } catch (e) {
      notify('Reset failed: ' + e.message);
    } finally {
      setBusy(null);
    }
  };

  const generate = async (shuffle = false) => {
    setBusy('generate');
    try {
      if (dirty) adopt(await fns.save(draft));
      const res = await fns.generate({ shuffle });
      if (res.ok) {
        setPreview(res.plan);
        setGenErrors([]);
        setState((s) => (s ? { ...s, plan_ready: true } : s));
        notify('Season generated');
      } else {
        setPreview(null);
        setGenErrors(res.errors || []);
        notify('No schedule satisfies these rules yet');
      }
    } catch (e) {
      notify('Generate failed: ' + e.message);
    } finally {
      setBusy(null);
    }
  };

  const apply = async () => {
    setBusy('apply');
    try {
      const res = await fns.apply();
      notify(res.changed
        ? `Schedule written to the save (${res.changed} matchups changed)`
        : 'The save already matches the generated schedule');
      adopt(await fns.load());
    } catch (e) {
      notify('Apply failed: ' + e.message);
    } finally {
      setBusy(null);
    }
  };

  const feasibility = useMemo(() => {
    if (!state) return null;
    const f = state.feasibility || { ok: true, errors: [], warnings: [] };
    if (!genErrors.length) return f;
    return { ...f, ok: false, errors: [...f.errors, ...genErrors] };
  }, [state, genErrors]);

  const gate = state?.apply_gate;
  const lockedWeeks = (state?.weeks || []).filter((w) => w.locked).map((w) => w.week);

  // one conference at a time: the active tab defaults to the user's own
  // conference and falls back to the first one the save carries. A picked
  // tab that no longer exists (rules reset, realigned save) falls back too.
  const conferences = state?.conferences || [];
  const validTab = (tab === NONCON_TAB || conferences.some((c) => c.name === tab)) ? tab : null;
  const activeTab = validTab
    || conferences.find((c) => c.name === state?.user_team?.conference)?.name
    || conferences[0]?.name
    || NONCON_TAB;
  const activeConf = conferences.find((c) => c.name === activeTab) || null;
  const rivCounts = useMemo(() => Object.fromEntries(
    Object.entries(draft?.conferences || {}).map(([name, c]) => [name, (c.rivalries || []).length]),
  ), [draft]);

  const body = error ? (
    <Callout tone="warn" title="Could not load the schedule editor">{error}</Callout>
  ) : !state ? (
    <div className="empty-state">Loading schedule rules...</div>
  ) : !state.available ? (
    <Callout tone="warn" title="Schedule editor unavailable">{state.reason}</Callout>
  ) : (
    <div className="sr-layout">
      <div className="sr-controls">
        <ScheduleConferenceTabs
          conferences={conferences}
          counts={rivCounts}
          nonconCount={(draft?.nonconference || []).length}
          active={activeTab}
          onChange={setTab}
        />
        {activeConf ? (
          <ConferenceScheduleCard
            key={activeConf.name}
            conference={activeConf}
            weeks={state.weeks}
            gameRivalries={state.game_rivalries || []}
            value={draft?.conferences?.[activeConf.name]}
            onChange={(v) => setDraft((d) => ({
              ...d,
              conferences: { ...d.conferences, [activeConf.name]: v },
            }))}
          />
        ) : (
          <NonConRivalsCard
            teams={allTeams}
            weeks={state.weeks}
            gameRivalries={state.game_rivalries || []}
            conferenceNames={conferences.map((c) => c.name)}
            value={draft?.nonconference || []}
            maxPerTeam={state.max_noncon_rivals}
            onChange={(nonconference) => setDraft((d) => ({ ...d, nonconference }))}
          />
        )}
      </div>
      <div className="sr-report">
        {gate && !gate.ok && (
          <Callout tone="warn" title="Schedule writes are closed right now">{gate.reason}</Callout>
        )}
        {gate && gate.ok && gate.full_reset && (
          <Callout tone="info" title="Full season rebuild">
            This is a preseason save with no locked weeks, so generating and applying here rebuilds the entire schedule, including Week 1. After applying, load the save in CFB 27 to play the new season.
          </Callout>
        )}
        {lockedWeeks.length > 0 && (
          <Callout tone="info" title="Some weeks are locked">
            {gate?.note
              || `The game has already locked week${lockedWeeks.length === 1 ? '' : 's'} ${lockedWeeks.join(', ')} in this save; those matchups are kept as they are and everything else schedules around them. To rebuild the whole season, including Week 1, apply to a save made during the preseason.`}
          </Callout>
        )}
        <ScheduleFeasibilityPanel feasibility={feasibility} />
        <PanelCard title="Generate">
          <div className="sr-row">
            <span className="sr-row-label">
              Build the season
              <span className="sr-row-sub">
                {dirty ? 'Saves your rules, then generates' : 'Uses the saved rules'}
              </span>
            </span>
            <span style={{ display: 'flex', gap: 8 }}>
              <Button onClick={() => generate(true)} disabled={busy != null}>Shuffle</Button>
              <Button variant="accent" onClick={() => generate(false)} spinning={busy === 'generate'} disabled={busy != null}>
                Generate Season
              </Button>
            </span>
          </div>
          <div className="sr-row">
            <span className="sr-row-label">
              Write it into the dynasty
              <span className="sr-row-sub">Close the dynasty in CFB 27 first, then load the save to play it</span>
            </span>
            <Button
              variant="accent"
              onClick={apply}
              spinning={busy === 'apply'}
              disabled={busy != null || !preview || !gate?.ok || dirty}
            >
              Apply to Save
            </Button>
          </div>
          {dirty && preview && (
            <p className="sr-nc-note">The rules changed since this season was generated; generate again before applying.</p>
          )}
        </PanelCard>
        {preview && <SchedulePreview preview={preview} userTeam={state.user_team} />}
      </div>
    </div>
  );

  return (
    <div className={embedded ? 'sr-embedded' : 'sr-embedded view-pad'}>
      <div className="sr-head">
        <h1>Schedule</h1>
        <Button variant="regen" onClick={reset} disabled={busy != null}>Reset Rules</Button>
        <Button variant="accent" onClick={save} spinning={busy === 'save'} disabled={busy != null || !dirty}>
          {busy === 'save' ? 'Saving' : 'Save Rules'}
        </Button>
      </div>
      {body}
    </div>
  );
}
