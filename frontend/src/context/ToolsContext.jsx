import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../lib/api.js';
import { readableAccent } from '../lib/format.js';

const ToolsContext = createContext(null);

export function useTools() {
  const context = useContext(ToolsContext);
  if (!context) throw new Error('useTools must be used within <ToolsProvider>');
  return context;
}

export function ToolsProvider({ children, setActive }) {
  const [config, setConfig] = useState(null);
  const [sim, setSim] = useState(null);
  const [simBusy, setSimBusy] = useState(false);
  const [budget, setBudget] = useState(null);
  const [team, setTeam] = useState({});
  const [fbsTeams, setFbsTeams] = useState([]);
  const [teamBusy, setTeamBusy] = useState(false);
  const [toastMsg, setToastMsg] = useState(null);
  const [ready, setReady] = useState(false);
  const [tick, setTick] = useState(0);

  const toast = useCallback((message) => {
    setToastMsg(message);
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => setToastMsg(null), 2600);
  }, []);

  const applyTheme = useCallback((nextTeam) => {
    if (!nextTeam) return;
    document.documentElement.style.setProperty(
      '--team', readableAccent(nextTeam.color, nextTeam.alt_color, '#e41c38'),
    );
    document.documentElement.style.setProperty(
      '--team-alt', readableAccent(nextTeam.alt_color, nextTeam.color, '#f5f5f5'),
    );
  }, []);

  const pointer = useMemo(
    () => ({ year: sim?.year || config?.sim?.year || 2026, week: sim?.week || 1 }),
    [sim, config],
  );

  const refreshSim = useCallback(async (year) => {
    try { setSim(await api.simState(year)); } catch { /* keep the last known state */ }
  }, []);

  const reloadBudget = useCallback(async () => {
    try { setBudget(await api.budget(pointer)); } catch { setBudget(null); }
  }, [pointer]);

  useEffect(() => {
    (async () => {
      try {
        const nextConfig = await api.config();
        setConfig(nextConfig);
        await refreshSim();
        try {
          const customization = await api.customization();
          const nextTeam = customization.values?.team || {};
          applyTheme(nextTeam);
          setTeam(nextTeam);
        } catch { /* retain the default theme */ }
        try { setFbsTeams((await api.simFbsTeams()).teams || []); } catch { /* picker stays empty */ }
        try { setBudget(await api.budget()); } catch { /* no budget before a season starts */ }
      } catch (error) {
        toast('Failed to connect to Dynasty+ Tools: ' + error.message);
      } finally {
        setReady(true);
      }
    })();
  }, [applyTheme, refreshSim, toast]);

  const afterSeasonChange = useCallback(async (year) => {
    await refreshSim(year);
    await reloadBudget();
    setTick((value) => value + 1);
  }, [refreshSim, reloadBudget]);

  const setUserTeam = useCallback(async (name) => {
    if (!name) return undefined;
    setTeamBusy(true);
    try {
      const result = await api.simSetTeam(name);
      const nextTeam = result?.team || {};
      setTeam(nextTeam);
      applyTheme(nextTeam);
      toast(`Team set: ${nextTeam.name || name}`);
      return result;
    } catch (error) {
      toast('Could not set team: ' + error.message);
      throw error;
    } finally {
      setTeamBusy(false);
    }
  }, [applyTheme, toast]);

  const startSeason = useCallback(async (year, seed) => {
    setSimBusy(true);
    try {
      const result = await api.simNew({ year, seed });
      if (result?.error) throw new Error(result.error);
      await afterSeasonChange(year);
      toast(`New season started: ${year}`);
      return result;
    } catch (error) {
      toast('Could not start season: ' + error.message);
      throw error;
    } finally {
      setSimBusy(false);
    }
  }, [afterSeasonChange, toast]);

  const simulateGame = useCallback(async (override) => {
    setSimBusy(true);
    try {
      const result = await api.simSimulateGame({ year: pointer.year, override });
      if (result?.error) throw new Error(result.error);
      await afterSeasonChange(pointer.year);
      toast(`Week ${result.week} game simulated. Advance when ready.`);
      return result;
    } catch (error) {
      toast('Simulation failed: ' + error.message);
      throw error;
    } finally {
      setSimBusy(false);
    }
  }, [pointer.year, afterSeasonChange, toast]);

  const advanceSim = useCallback(async (override) => {
    setSimBusy(true);
    try {
      const result = await api.simAdvance({ year: pointer.year, override });
      if (result?.error) throw new Error(result.error);
      await afterSeasonChange(pointer.year);
      toast(`Advanced to Week ${result.week + 1 > (sim?.weeks_total || 99) ? result.week : result.week + 1}`);
      return result;
    } catch (error) {
      toast('Simulation failed: ' + error.message);
      throw error;
    } finally {
      setSimBusy(false);
    }
  }, [pointer.year, afterSeasonChange, toast, sim]);

  const resetSim = useCallback(async () => {
    try {
      await api.simReset({ year: pointer.year });
      await afterSeasonChange(pointer.year);
      toast('Simulation reset');
    } catch (error) {
      toast('Reset failed: ' + error.message);
    }
  }, [pointer.year, afterSeasonChange, toast]);

  const deleteDynasty = useCallback(async () => {
    setSimBusy(true);
    try {
      await api.simDelete();
      await refreshSim();
      try {
        const customization = await api.customization();
        const nextTeam = customization.values?.team || {};
        applyTheme(nextTeam);
        setTeam(nextTeam);
      } catch { /* retain the current theme */ }
      setBudget(null);
      setTick((value) => value + 1);
      toast('Dynasty deleted. Starting from scratch.');
    } catch (error) {
      toast('Delete failed: ' + error.message);
      throw error;
    } finally {
      setSimBusy(false);
    }
  }, [refreshSim, applyTheme, toast]);

  const closeSettings = useCallback(async () => {
    setActive('dashboard');
    try {
      const customization = await api.customization();
      const nextTeam = customization.values?.team || {};
      applyTheme(nextTeam);
      setTeam(nextTeam);
    } catch { /* ignore */ }
    await reloadBudget();
    setTick((value) => value + 1);
  }, [setActive, applyTheme, reloadBudget]);

  const value = {
    config, ready, pointer, toast, toastMsg,
    sim, simBusy, simActive: !!sim?.active,
    startSeason, simulateGame, advanceSim, resetSim, deleteDynasty, refreshSim,
    budget, setBudget, reloadBudget,
    team, fbsTeams, teamBusy, setUserTeam,
    closeSettings,
    reloadKey: tick,
  };

  return <ToolsContext.Provider value={value}>{children}</ToolsContext.Provider>;
}
