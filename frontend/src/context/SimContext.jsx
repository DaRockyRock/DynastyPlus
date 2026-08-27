import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { AppContext } from './AppContext.jsx';
import { api } from '../lib/api.js';
import { readableAccent } from '../lib/format.js';

// The Simulator's provider. It reuses the SAME AppContext the companion pages
// read from (useApp), but supplies a Simulator-flavored value: it drives the
// season (start / simulate / override / reset), owns the authoritative budget,
// and edits game-data customization. Pages and hooks built for the companion
// (DebugPage, SettingsPage, NilPage, useBudget) work unchanged because they only
// read fields off useApp(); the phone/news fields they never touch are stubbed.
export function SimProvider({ children, active, setActive }) {
  const [config, setConfig] = useState(null);
  const [sim, setSim] = useState(null);
  const [simBusy, setSimBusy] = useState(false);
  const [budget, setBudget] = useState(null);
  const [team, setTeam] = useState({});
  const [fbsTeams, setFbsTeams] = useState([]);
  const [teamBusy, setTeamBusy] = useState(false);
  const [pending, setPending] = useState([]);
  const [toastMsg, setToastMsg] = useState(null);
  const [ready, setReady] = useState(false);
  const [tick, setTick] = useState(0);

  const toast = useCallback((msg) => {
    setToastMsg(msg);
    clearTimeout(toast._t);
    toast._t = setTimeout(() => setToastMsg(null), 2600);
  }, []);

  const applyTheme = useCallback((team) => {
    if (!team) return;
    // A black/near-black primary (e.g. UCF) would vanish on the dark field, so
    // fall back to the secondary color when the primary is not visible.
    document.documentElement.style.setProperty('--team', readableAccent(team.color, team.alt_color, '#e41c38'));
    document.documentElement.style.setProperty('--team-alt', readableAccent(team.alt_color, team.color, '#f5f5f5'));
  }, []);

  const pointer = useMemo(
    () => ({ year: sim?.year || config?.sim?.year || 2026, week: sim?.week || 1 }),
    [sim, config],
  );

  const refreshSim = useCallback(async (year) => {
    try { setSim(await api.simState(year)); } catch { /* keep last-known */ }
  }, []);

  const reloadBudget = useCallback(async () => {
    try { setBudget(await api.budget(pointer)); } catch { setBudget(null); }
  }, [pointer]);

  const reloadInbox = useCallback(async (year) => {
    try { const r = await api.inbox({ year: year ?? pointer.year }); setPending(r.pending || []); }
    catch { setPending([]); }
  }, [pointer.year]);

  // boot: config + sim state + theme (from the game-data team) + budget.
  useEffect(() => {
    (async () => {
      try {
        const cfg = await api.config();
        setConfig(cfg);
        await refreshSim();
        try {
          const cz = await api.customization();
          applyTheme(cz.values?.team);
          setTeam(cz.values?.team || {});
        } catch { /* theme stays default */ }
        try { setFbsTeams((await api.simFbsTeams()).teams || []); } catch { /* picker stays empty */ }
        try { setBudget(await api.budget()); } catch { /* none until a season */ }
        reloadInbox();
      } catch (e) {
        toast('Failed to connect to the Simulator backend: ' + e.message);
      } finally {
        setReady(true);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const afterSeasonChange = useCallback(async (year) => {
    await refreshSim(year);
    await reloadBudget();
    await reloadInbox(year);
    setTick((t) => t + 1);
  }, [refreshSim, reloadBudget, reloadInbox]);

  // Swap the user's program before a season starts. Persists the full identity
  // (name, colors, conference, logo) into game data and reskins the app; the
  // companion picks up the team's real local writers on its next Scan. Blocked
  // server-side once a season is active.
  const setUserTeam = useCallback(async (name) => {
    if (!name) return;
    setTeamBusy(true);
    try {
      const res = await api.simSetTeam(name);
      const t = res?.team || {};
      setTeam(t);
      applyTheme(t);
      toast(`Team set: ${t.name || name}`);
      return res;
    } catch (e) {
      toast('Could not set team: ' + e.message);
      throw e;
    } finally {
      setTeamBusy(false);
    }
  }, [applyTheme, toast]);

  const startSeason = useCallback(async (year, seed) => {
    setSimBusy(true);
    try {
      const res = await api.simNew({ year, seed });
      if (res?.error) throw new Error(res.error);
      await afterSeasonChange(year);
      toast(`New season started: ${year}`);
      return res;
    } catch (e) {
      toast('Could not start season: ' + e.message);
      throw e;
    } finally {
      setSimBusy(false);
    }
  }, [afterSeasonChange, toast]);

  // Play the current week's games but STAY on the week, so the companion can run
  // the post-game press conference and reflect the result in this week's coverage.
  // Advancing (below) is a separate step.
  const simulateGame = useCallback(async (override) => {
    setSimBusy(true);
    try {
      const res = await api.simSimulateGame({ year: pointer.year, override });
      if (res?.error) throw new Error(res.error);
      await afterSeasonChange(pointer.year);
      toast(`Week ${res.week} game simulated. Answer the post-game presser in Dynasty+, then advance when ready.`);
      return res;
    } catch (e) {
      toast('Simulation failed: ' + e.message);
      throw e;
    } finally {
      setSimBusy(false);
    }
  }, [pointer.year, afterSeasonChange, toast]);

  const advanceSim = useCallback(async (override) => {
    setSimBusy(true);
    try {
      const res = await api.simAdvance({ year: pointer.year, override });
      if (res?.error) throw new Error(res.error);
      await afterSeasonChange(pointer.year);
      const applied = (res.applied_actions || []).length;
      toast(`Advanced to Week ${res.week + 1 > (sim?.weeks_total || 99) ? res.week : res.week + 1}` + (applied ? ` (applied ${applied} coach action${applied > 1 ? 's' : ''})` : ''));
      return res;
    } catch (e) {
      toast('Simulation failed: ' + e.message);
      throw e;
    } finally {
      setSimBusy(false);
    }
  }, [pointer.year, afterSeasonChange, toast, sim]);

  const resetSim = useCallback(async () => {
    try {
      await api.simReset({ year: pointer.year });
      await afterSeasonChange(pointer.year);
      toast('Simulation reset');
    } catch (e) {
      toast('Reset failed: ' + e.message);
    }
  }, [pointer.year, afterSeasonChange, toast]);

  // Full clean slate: deletes every season and all generated content, then resets
  // customization to defaults (so the team identity reverts too). Re-reads the
  // now-default team to reskin the app and drops the stale budget/inbox state.
  const deleteDynasty = useCallback(async () => {
    setSimBusy(true);
    try {
      await api.simDelete();
      await refreshSim();
      try {
        const cz = await api.customization();
        applyTheme(cz.values?.team);
        setTeam(cz.values?.team || {});
      } catch { /* theme stays as-is */ }
      setBudget(null);
      setPending([]);
      setTick((t) => t + 1);
      toast('Dynasty deleted. Starting from scratch.');
    } catch (e) {
      toast('Delete failed: ' + e.message);
      throw e;
    } finally {
      setSimBusy(false);
    }
  }, [refreshSim, applyTheme, toast]);

  // Customize close returns to the dashboard tab (it is a tab here, not an overlay).
  const closeSettings = useCallback(async () => {
    setActive('dashboard');
    try {
      const cz = await api.customization();
      applyTheme(cz.values?.team);
      setTeam(cz.values?.team || {});
    } catch { /* ignore */ }
    await reloadBudget();
    setTick((t) => t + 1);
  }, [setActive, applyTheme, reloadBudget]);

  const value = {
    // identity for the reused pages/hooks
    app: 'simulator',
    config, ready, pointer, toast, toastMsg,
    // sim driver
    sim, simBusy, simActive: !!sim?.active, debugMode: true,
    startSeason, simulateGame, advanceSim, resetSim, deleteDynasty, refreshSim,
    // authoritative budget (the Simulator owns the store)
    budget, setBudget, reloadBudget,
    // game-data identity + queued companion actions, for the shell chrome
    team, pending, reloadInbox,
    // FBS team picker (season-start screen)
    fbsTeams, teamBusy, setUserTeam,
    // customize
    closeSettings,
    // stubs for companion-only surfaces the reused pages reference but the
    // Simulator does not have (no phone, no media generation).
    contactForName: () => null,
    appendThread: () => {},
    textPerson: () => {},
    // a refetch nonce the reused hooks key off
    reloadKey: tick,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
