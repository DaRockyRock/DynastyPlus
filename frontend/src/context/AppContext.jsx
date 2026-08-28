import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../lib/api.js';
import { readableAccent } from '../lib/format.js';
import { registerConferences } from '../lib/conferences.js';

export const AppContext = createContext(null);

const LIVE_POLL_MS = 4000;
const SAVE_SYNC_POLL_MS = 600;

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within <AppProvider>');
  return ctx;
}

export function AppProvider({ children }) {
  const [config, setConfig] = useState(null);
  const [dynasty, setDynasty] = useState(null);
  const [pointer, setPointer] = useState({ year: 2026, week: 1 });
  const [ready, setReady] = useState(false);
  const [loading] = useState({
    active: false, week: null, progress: 0, total: 0, module: null, subStep: null,
  });
  const [toastMsg, setToastMsg] = useState(null);
  const toastTimerRef = useRef(null);

  const [setup, setSetup] = useState({ loading: true });
  const [setupOpen, setSetupOpen] = useState(false);
  const setupPollRef = useRef(null);

  const [activeTab, setActiveTab] = useState('conferences');
  const [dynastyLib, setDynastyLib] = useState({
    dynasties: [], current: null, save_present: false,
    save_hash: null, current_hash: null,
  });
  const [enteredDynasty, setEnteredDynasty] = useState(null);
  const [bowlGamesReady, setBowlGamesReady] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [autosyncBusy, setAutosyncBusy] = useState(false);
  const [saveAutomation, setSaveAutomation] = useState({
    phase: 'idle', running: false, reload_required: false,
  });

  const scanBusyRef = useRef(false);
  const lastHashRef = useRef(null);

  const toast = useCallback((message) => {
    setToastMsg(message);
    clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setToastMsg(null), 2600);
  }, []);

  const applyTheme = useCallback((team) => {
    if (!team) return;
    document.documentElement.style.setProperty(
      '--team', readableAccent(team.color, team.alt_color, '#e41c38'),
    );
    document.documentElement.style.setProperty(
      '--team-alt', readableAccent(team.alt_color, team.color, '#f5f5f5'),
    );
  }, []);

  const loadDynasty = useCallback(async (year, week) => {
    const res = await api.dynasty(year, week);
    setDynasty(res.dynasty);
    applyTheme(res.dynasty?.team);
    api.bowlGames()
      .then((bowls) => setBowlGamesReady(!!bowls?.available))
      .catch(() => setBowlGamesReady(false));
    return res.dynasty;
  }, [applyTheme]);

  const refreshDynasties = useCallback(async () => {
    try {
      const lib = await api.dynasties();
      setDynastyLib(lib);
      return lib;
    } catch {
      return null;
    }
  }, []);

  const browseSaves = useCallback(async () => {
    try {
      const { saves } = await api.browseSaves();
      return saves || [];
    } catch (error) {
      toast('Could not read the saves folder: ' + error.message);
      return [];
    }
  }, [toast]);

  const loadSaveTeams = useCallback(async (path) => {
    try {
      const { teams } = await api.saveTeams(path);
      return teams || [];
    } catch {
      return [];
    }
  }, []);

  const importSave = useCallback(async (path, school) => {
    try {
      const { dynasty: entry } = await api.importDynasty(path, school);
      await refreshDynasties();
      toast(`Imported ${entry.team_name}`);
      return entry;
    } catch (error) {
      toast('Could not import that save: ' + error.message);
      return null;
    }
  }, [refreshDynasties, toast]);

  const removeDynasty = useCallback(async (id) => {
    try {
      await api.removeDynasty(id);
      await refreshDynasties();
      toast('Removed from the Dynasty+ library');
      return true;
    } catch (error) {
      toast('Could not remove that dynasty: ' + error.message);
      return false;
    }
  }, [refreshDynasties, toast]);

  useEffect(() => {
    (async () => {
      try {
        const [cfg, lib] = await Promise.all([api.config(), api.dynasties()]);
        setConfig(cfg);
        setDynastyLib(lib);
      } catch (error) {
        toast('Failed to connect to backend: ' + error.message);
      } finally {
        setReady(true);
      }
    })();
  }, [toast]);

  const refreshSetup = useCallback(async () => {
    try {
      const [status, detected] = await Promise.all([
        api.setupStatus(),
        api.setupDetect().catch(() => ({ installs: [], saves: [] })),
      ]);
      setSetup((prev) => ({ ...prev, ...status, detected, loading: false }));
      return status;
    } catch {
      setSetup((prev) => ({ ...prev, loading: false }));
      return null;
    }
  }, []);

  const browseFolder = useCallback(async (options) => {
    if (typeof window !== 'undefined' && window.desktop?.pickFolder) {
      try { return await window.desktop.pickFolder(options || {}); }
      catch { return null; }
    }
    return null;
  }, []);

  const setSavePath = useCallback(async (path) => {
    if (!path) return;
    try {
      await api.setupPaths({ save_path: path });
      await refreshSetup();
    } catch (error) {
      toast('Could not set the saves folder: ' + error.message);
    }
  }, [refreshSetup, toast]);

  const setGameRoot = useCallback(async (path) => {
    if (!path) return;
    try {
      await api.setupPaths({ game_root: path });
      await refreshSetup();
    } catch (error) {
      toast('Could not set the game folder: ' + error.message);
    }
  }, [refreshSetup, toast]);

  const pollExtract = useCallback(() => {
    clearTimeout(setupPollRef.current);
    const poll = async () => {
      try {
        const job = await api.setupExtractStatus();
        setSetup((prev) => ({
          ...prev,
          extracting: job.running,
          stage: job.stage,
          done: job.done,
          total: job.total,
          error: job.error,
          summary: job.summary,
        }));
        if (!job.running) {
          await refreshSetup();
          if (job.error) toast('Game art extraction failed: ' + job.error);
          return;
        }
      } catch { /* transient */ }
      setupPollRef.current = setTimeout(poll, 700);
    };
    setupPollRef.current = setTimeout(poll, 500);
  }, [refreshSetup, toast]);

  const runExtraction = useCallback(async (gameRoot) => {
    setSetup((prev) => ({
      ...prev, extracting: true, error: null, summary: null,
      stage: 'starting', done: 0, total: 0,
    }));
    try {
      await api.setupExtract(gameRoot ? { game_root: gameRoot } : {});
      pollExtract();
    } catch (error) {
      setSetup((prev) => ({
        ...prev,
        extracting: false,
        error: error.message === 'not_an_install'
          ? 'That folder is not a College Football 27 install.'
          : error.message,
      }));
    }
  }, [pollExtract]);

  useEffect(() => {
    (async () => {
      const status = await refreshSetup();
      if (status && !status.complete) setSetupOpen(true);
    })();
    return () => {
      clearTimeout(setupPollRef.current);
      clearTimeout(toastTimerRef.current);
    };
  }, [refreshSetup]);

  useEffect(() => {
    if (!enteredDynasty) return;
    api.conferences()
      .then((map) => registerConferences(Object.values(map || {})))
      .catch(() => {});
  }, [enteredDynasty]);

  const autosyncEnabled = config?.autosync_enabled !== false;
  const setAutosync = useCallback(async (enabled) => {
    setAutosyncBusy(true);
    setConfig((current) => ({ ...(current || {}), autosync_enabled: enabled }));
    try {
      const result = await api.setAutosync(enabled);
      setConfig((current) => ({
        ...(current || {}), autosync_enabled: result.autosync_enabled,
      }));
      toast(enabled ? 'Auto-sync on' : 'Auto-sync off');
    } catch {
      setConfig((current) => ({ ...(current || {}), autosync_enabled: !enabled }));
      toast('Could not change auto-sync');
    } finally {
      setAutosyncBusy(false);
    }
  }, [toast]);

  const scan = useCallback(async () => {
    if (scanBusyRef.current) return null;
    scanBusyRef.current = true;
    setScanning(true);
    try {
      const result = await api.scan();
      await refreshDynasties();
      if (result?.save_automation) setSaveAutomation(result.save_automation);
      const saveWork = result?.save_automation;
      if (saveWork?.running || saveWork?.reload_required || saveWork?.phase === 'error') {
        return result;
      }
      if (enteredDynasty && result?.dynasty) {
        const next = { year: result.year, week: result.week };
        setPointer(next);
        lastHashRef.current = result.dynasty.hash || null;
        setEnteredDynasty(result.dynasty);
        await loadDynasty(next.year, next.week);
      }
      toast(result?.dynasty
        ? `Scanned ${result.dynasty.team_name} (Week ${result.week})`
        : 'Scan complete');
      return result;
    } catch (error) {
      toast(error.message || 'No CFB 27 dynasty save was found.');
      return { present: false, error: error.message };
    } finally {
      setScanning(false);
      scanBusyRef.current = false;
    }
  }, [enteredDynasty, loadDynasty, refreshDynasties, toast]);

  const continueSaveAutomation = useCallback(async () => {
    try {
      if (saveAutomation?.phase === 'error') {
        await api.saveRecruitingTool({ enabled: false });
      }
      const result = await api.recruitingReloadComplete();
      setSaveAutomation(result.automation || {
        phase: 'idle', running: false, reload_required: false,
      });
      return await scan();
    } catch (error) {
      toast('Could not continue the week sync: ' + error.message);
      return null;
    }
  }, [saveAutomation, scan, toast]);

  const selectDynasty = useCallback(async (id) => {
    try {
      const { dynasty: entry } = await api.selectDynasty(id);
      const next = { year: entry.year, week: entry.week };
      setPointer(next);
      lastHashRef.current = entry.hash || null;
      await loadDynasty(next.year, next.week);
      setEnteredDynasty(entry);
      setActiveTab('conferences');
    } catch (error) {
      toast('Could not open that dynasty: ' + error.message);
    }
  }, [loadDynasty, toast]);

  const exitDynasty = useCallback(() => {
    setEnteredDynasty(null);
    setDynasty(null);
    setBowlGamesReady(false);
    refreshDynasties();
  }, [refreshDynasties]);

  useEffect(() => {
    if (!enteredDynasty) return undefined;
    let cancelled = false;
    let timer;
    const poll = async () => {
      let automation;
      try {
        const state = await api.state();
        const save = state?.save;
        automation = state?.save_automation;
        if (!cancelled && automation) setSaveAutomation(automation);
        const saveWorkActive = automation?.running
          || automation?.reload_required
          || automation?.phase === 'error';
        if (!cancelled && save?.present && !scanBusyRef.current && !saveWorkActive) {
          const advanced = save.year > pointer.year
            || (save.year === pointer.year && save.week > pointer.week);
          const changed = save.year === pointer.year
            && save.week === pointer.week
            && save.hash
            && save.hash !== lastHashRef.current;
          if (advanced || changed) await scan();
        }
      } catch { /* transient */ }
      if (!cancelled) {
        timer = setTimeout(
          poll,
          automation?.running ? SAVE_SYNC_POLL_MS : LIVE_POLL_MS,
        );
      }
    };
    timer = setTimeout(poll, LIVE_POLL_MS);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [enteredDynasty, pointer, scan]);

  const value = {
    app: 'tools',
    config,
    dynasty,
    pointer,
    ready,
    mode: 'live',
    watcherActive: !!config?.watcher?.active,
    autosyncEnabled,
    autosyncBusy,
    setAutosync,
    loading,
    toastMsg,
    toast,
    dynastyLib,
    enteredDynasty,
    bowlGamesReady,
    scanning,
    refreshDynasties,
    scan,
    scanNow: scan,
    selectDynasty,
    removeDynasty,
    exitDynasty,
    saveAutomation,
    continueSaveAutomation,
    browseSaves,
    loadSaveTeams,
    importSave,
    setup,
    setupOpen,
    openSetup: () => setSetupOpen(true),
    closeSetup: () => setSetupOpen(false),
    refreshSetup,
    browseFolder,
    setSavePath,
    setGameRoot,
    runExtraction,
    activeTab,
    setActiveTab,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
