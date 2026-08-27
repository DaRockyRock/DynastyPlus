import { createContext, useContext, useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { api } from '../lib/api.js';
import { readableAccent } from '../lib/format.js';

export const AppContext = createContext(null);

// How often the live experience polls the backend for watcher-driven changes.
const LIVE_POLL_MS = 4000;

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within <AppProvider>');
  return ctx;
}

export function AppProvider({ children }) {
  const [config, setConfig] = useState(null);
  const [dynasty, setDynasty] = useState(null);
  const [pointer, setPointer] = useState({ year: 2026, week: 10 });
  const [loading, setLoading] = useState({ active: false, week: null, progress: 0, total: 0, module: null, subStep: null });
  const [toastMsg, setToastMsg] = useState(null);
  const [phoneOpen, setPhoneOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [article, setArticle] = useState(null);
  const [ready, setReady] = useState(false);
  // Phone contacts + conversation threads live here (not in PhoneApp) so an NIL
  // offer made anywhere can drop a text into the right recruit's chat.
  const [phoneContacts, setPhoneContacts] = useState([]);
  const [phoneCategories, setPhoneCategories] = useState([]);
  const [phoneThreads, setPhoneThreads] = useState({});
  // The social feed (the phone's second app): the week's generated posts plus the
  // coach's interaction state (which posts he liked, and which weeks he has read).
  const [feedPosts, setFeedPosts] = useState([]);
  const [feedLikes, setFeedLikes] = useState({});
  const [feedSeen, setFeedSeen] = useState({});
  // Which conversation the phone is showing (null = the contact list). Lifted
  // here so hovering any name in the app can open the phone straight to a chat.
  const [activeChatId, setActiveChatId] = useState(null);
  // Which top-level tab is showing. Lifted here so a result card (or the presser)
  // can jump straight to the Game Center.
  const [activeTab, setActiveTab] = useState('home');
  // The post-game press conference, when one is open (the live interview state
  // from /api/interview/*). Null when there is no presser to run.
  const [presser, setPresser] = useState(null);
  const reloadKey = useRef(0);
  const [tick, setTick] = useState(0);
  // Coach actions queued for the Simulator (from /api/state). Shown in the chrome.
  const [pendingActions, setPendingActions] = useState(0);
  // Highest (year, week) the backend has reported. The live loop only pulls the
  // view forward when the watcher advances past this, so browsing older weeks is
  // not yanked away on every poll.
  const latestSeenRef = useRef({ year: 2026, week: 10 });
  // The save's content hash, so a re-scan can tell whether the Simulator wrote
  // a newer week/state than the one currently loaded.
  const lastHashRef = useRef(null);
  // The world-reaction log version. When it bumps (the coach said something the
  // world reacted to), the feed has fresh coach-caused posts to pull in.
  const worldVersionRef = useRef(null);
  // The count of coach actions queued for the Simulator, last observed. When it
  // drops (the Simulator drained and applied them), the save's budget has updated,
  // so we pull the authoritative budget WITHOUT regenerating media.
  const pendingRef = useRef(0);
  // The dynasty library + which one (if any) the coach has entered. The app
  // opens to the library and stays passive until the coach Scans + Continues.
  const [dynastyLib, setDynastyLib] = useState({ dynasties: [], current: null, save_present: false, save_hash: null, current_hash: null });
  const [enteredDynasty, setEnteredDynasty] = useState(null);
  const [scanning, setScanning] = useState(false);
  // Guards against a manual scan and the live watch firing at the same time.
  const scanBusyRef = useRef(false);

  const toast = useCallback((msg) => {
    setToastMsg(msg);
    clearTimeout(toast._t);
    toast._t = setTimeout(() => setToastMsg(null), 2600);
  }, []);

  const applyTheme = useCallback((team) => {
    if (!team) return;
    // Use the primary color when it is visible on the dark field, otherwise fall
    // back to the secondary (a black/near-black primary like UCF's would vanish).
    document.documentElement.style.setProperty('--team', readableAccent(team.color, team.alt_color, '#e41c38'));
    document.documentElement.style.setProperty('--team-alt', readableAccent(team.alt_color, team.color, '#f5f5f5'));
  }, []);

  const loadDynasty = useCallback(async (year, week) => {
    const res = await api.dynasty(year, week);
    setDynasty(res.dynasty);
    applyTheme(res.dynasty.team);
    return res.dynasty;
  }, [applyTheme]);

  const refreshDynasties = useCallback(async () => {
    try { const lib = await api.dynasties(); setDynastyLib(lib); return lib; }
    catch { return null; }
  }, []);

  // Boot into the dynasty library. Do not load a dynasty until the user scans
  // and selects one.
  // the app opens to the library and waits for the coach to Scan + Continue.
  useEffect(() => {
    (async () => {
      try {
        const [cfg, lib] = await Promise.all([api.config(), api.dynasties()]);
        setConfig(cfg);
        if (lib) setDynastyLib(lib);
      } catch (e) {
        toast('Failed to connect to backend: ' + e.message);
      } finally {
        setReady(true);
      }
    })();
  }, [toast]);

  // Reload the phone roster + persisted threads for the current week. The roster
  // also maps an NIL offer to the right recruit's chat, and the threads carry the
  // unprompted texts people send the coach week to week (with their unread flags).
  const refreshPhone = useCallback(async (p = pointer) => {
    try {
      const d = await api.module('phone', p);
      setPhoneContacts(d.contacts || []);
      setPhoneCategories(d.categories || []);
    } catch { /* keep last-known */ }
    try {
      const t = await api.phoneThreads(p);
      setPhoneThreads(t.threads || {});
    } catch { /* keep last-known */ }
  }, [pointer]);

  // Reload the week's social feed (the timeline) and the coach's like/seen state.
  const refreshFeed = useCallback(async (p = pointer) => {
    try {
      const d = await api.module('feed', p);
      setFeedPosts(d.posts || []);
    } catch { /* keep last-known */ }
    try {
      const s = await api.feedState(p);
      setFeedLikes(s.likes || {});
      setFeedSeen(s.seen || {});
    } catch { /* keep last-known */ }
  }, [pointer]);

  // Load once a dynasty is entered and whenever the week changes, so a text that
  // arrived with the new week shows up in Messages, and the new week's feed loads.
  useEffect(() => {
    if (enteredDynasty) { refreshPhone(); refreshFeed(); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enteredDynasty, pointer.year, pointer.week]);

  // When a generation pass finishes (boot prewarm, Advance Week, simulation),
  // pull in any inbound texts and feed posts it produced for the current week.
  const wasLoadingRef = useRef(false);
  useEffect(() => {
    if (ready && wasLoadingRef.current && !loading.active) { refreshPhone(); refreshFeed(); }
    wasLoadingRef.current = loading.active;
  }, [ready, loading.active, refreshPhone, refreshFeed]);

  const appendThread = useCallback((contactId, items) => {
    if (!contactId || !items || !items.length) return;
    // Stamp a timestamp so the conversation sorts to the top by recency, matching
    // how the backend stamps persisted messages.
    const now = Date.now() / 1000;
    const stamped = items.map((it) => (it && it.ts ? it : { ...it, ts: now }));
    setPhoneThreads((t) => ({ ...t, [contactId]: [...(t[contactId] || []), ...stamped] }));
  }, []);

  // Unread inbound texts, derived from the threads (the single source of truth).
  // A bubble carries `unread: true` until the coach opens that conversation.
  const unreadByContact = useMemo(() => {
    const m = {};
    for (const [cid, items] of Object.entries(phoneThreads)) {
      const n = (items || []).filter((it) => it && it.unread).length;
      if (n) m[cid] = n;
    }
    return m;
  }, [phoneThreads]);
  const unreadTotal = useMemo(
    () => Object.values(unreadByContact).reduce((a, b) => a + b, 0),
    [unreadByContact],
  );

  // Like a feed post: optimistic local toggle plus a server write so the like
  // persists across reloads (post ids are stable across regeneration).
  const toggleFeedLike = useCallback((postId) => {
    if (!postId) return;
    setFeedLikes((l) => {
      const next = { ...l };
      if (next[postId]) delete next[postId]; else next[postId] = true;
      return next;
    });
    api.feedLike(postId).catch(() => {});
  }, []);

  // Opening the Feed marks the week read, clearing its unseen badge.
  const markFeedSeen = useCallback((week) => {
    if (week == null) return;
    setFeedSeen((s) => (s[String(week)] ? s : { ...s, [String(week)]: Date.now() / 1000 }));
    api.feedSeen(week).catch(() => {});
  }, []);

  // Unseen-post badge for the current week: the whole timeline until the coach
  // opens the Feed for this week, then zero.
  const feedUnseen = useMemo(
    () => (feedSeen[String(pointer.week)] ? 0 : feedPosts.length),
    [feedSeen, feedPosts, pointer.week],
  );

  // The coach opened a conversation: clear its unread texts locally and on the
  // server so the badge updates immediately and stays cleared across reloads.
  const markThreadRead = useCallback((contactId) => {
    if (!contactId) return;
    setPhoneThreads((t) => {
      const items = t[contactId];
      if (!items || !items.some((it) => it && it.unread)) return t;
      const next = items.map((it) => {
        if (!it || !it.unread) return it;
        const { unread, ...rest } = it;
        return rest;
      });
      return { ...t, [contactId]: next };
    });
    api.phoneRead(contactId).catch(() => {});
  }, []);

  // NIL / Dynasty Points budget snapshot. Shared app-wide so the persistent
  // budget bar (above the tabs) and every surface stay in sync; offers made
  // anywhere fold their fresh snapshot back in via setBudget.
  const [budget, setBudget] = useState(null);
  const reloadBudget = useCallback(async () => {
    try { setBudget(await api.budget(pointer)); } catch { /* keep last-known */ }
  }, [pointer]);

  const contactForName = useCallback(
    (name) => phoneContacts.find((c) => c.entity && c.entity.name === name) || null,
    [phoneContacts],
  );

  // Text anyone. Resolves a hovered name (with a kind hint) into a contact on the
  // backend, drops it into the roster + threads if new, then opens the phone to
  // that conversation. Reused names map back to their existing thread server-side.
  const textPerson = useCallback(async ({ name, kind, role, team } = {}) => {
    if (!name) return;
    try {
      const { contact } = await api.phoneOpen({ name, kind, role, team });
      if (!contact) return;
      setPhoneContacts((list) => (list.some((c) => c.id === contact.id) ? list : [contact, ...list]));
      setPhoneThreads((t) => (t[contact.id] ? t : { ...t, [contact.id]: [] }));
      setActiveChatId(contact.id);
      setPhoneOpen(true);
    } catch (e) {
      toast('Could not open that chat: ' + e.message);
    }
  }, [toast]);

  // Refetch the budget once a dynasty is entered and whenever the week refreshes.
  useEffect(() => { if (enteredDynasty) reloadBudget(); }, [enteredDynasty, reloadBudget, tick]);

  // Customize flow. Opening pauses the live experience visually; closing pulls
  // every edit back into the running app (identity/theme, roster, phone roster,
  // and all cached module content, which the backend invalidated on save).
  const openSettings = useCallback(() => setSettingsOpen(true), []);
  const closeSettings = useCallback(async () => {
    setSettingsOpen(false);
    try {
      await loadDynasty(pointer.year, pointer.week);
      const d = await api.module('phone', pointer);
      setPhoneContacts(d.contacts || []);
      setPhoneCategories(d.categories || []);
    } catch { /* ignore - app keeps last-known state */ }
    reloadKey.current += 1;
    setTick((t) => t + 1);
  }, [loadDynasty, pointer]);

  const goToWeek = useCallback(async (week) => {
    if (week < 1) return;
    const next = { ...pointer, week };
    setPointer(next);
    await loadDynasty(next.year, week);
    reloadKey.current += 1;
    setTick((t) => t + 1);
    toast(`Viewing Week ${week}`);
  }, [pointer, loadDynasty, toast]);

  // Dynasty+ always passively watches the save the Simulator (or, later, CFB 27)
  // writes; the Simulator is what advances weeks. There is no manual advance and
  // no in-app simulation here anymore.
  const mode = 'live';
  const watcherActive = !!config?.watcher?.active;

  // Generate the entire week's media up front behind the blocking overlay, so
  // entering or re-scanning shows a finished slate instead of each tab loading
  // in one by one. Polls the pipeline status to narrate progress, and the
  // overlay blocks interaction until generation finishes.
  const generateWeek = useCallback(async ({ year, week }, { regenerate = false } = {}) => {
    setLoading({ active: true, week, progress: 0, total: 0, module: null, subStep: null });
    let done = false;
    const gen = api.generate({ year, week, regenerate }).catch(() => {}).finally(() => { done = true; });
    while (!done) {
      try {
        const st = await api.status();
        if (st && st.running) {
          setLoading((prev) => ({ ...prev, progress: st.progress || 0, total: st.total || 0, module: st.module, subStep: st.sub_step || null }));
        }
      } catch { /* keep polling */ }
      await new Promise((r) => setTimeout(r, 300));
    }
    await gen;
    setLoading({ active: false, week: null, progress: 0, total: 0, module: null, subStep: null });
  }, []);

  // --- post-game press conference -----------------------------------------
  // After the presser, the backend builds the week's coverage in the background
  // (the post-game news always, plus the rest of the new week when a game was
  // advanced). We do NOT block on it: the coach lands on the Game Center and the
  // other tabs fill in as the pass finishes. Poll quietly and pull the results in
  // when the pass settles (no loading overlay), so a slow model never strands the
  // page on stale content the way a fixed timeout did. The live-poll loop's
  // world-version refresh is a second safety net for a newsworthy presser.
  const refreshAfterPresser = useCallback(async (p) => {
    await new Promise((r) => setTimeout(r, 400)); // let the background thread start
    let sawRunning = false;
    for (let i = 0; i < 360; i += 1) {
      let st = null;
      try { st = await api.status(); } catch { /* keep polling */ }
      if (st && st.running) sawRunning = true;
      if (st && !st.running && (sawRunning || i > 2)) break;
      await new Promise((r) => setTimeout(r, 500));
    }
    reloadKey.current += 1;
    setTick((t) => t + 1);
    await refreshPhone(p);
    await refreshFeed(p);
  }, [refreshPhone, refreshFeed]);

  // If the user's last game has an unfinished presser, open it (start or resume).
  // While the first question generates, show a post-game overlay so the user sees
  // what is happening (the press conference, not a week advance).
  const maybeOpenPresser = useCallback(async (p) => {
    try {
      const { pending } = await api.interviewPending(p);
      if (!pending) return false;
      setLoading({ active: true, week: p.week, progress: 0, total: 0, module: null, subStep: null,
        title: 'Post-game', caption: 'Heading to the press conference' });
      const state = await api.interviewStart(p);
      setLoading({ active: false, week: null, progress: 0, total: 0, module: null, subStep: null });
      if (state && state.status !== 'complete') { setPresser(state); return true; }
    } catch {
      setLoading({ active: false, week: null, progress: 0, total: 0, module: null, subStep: null });
    }
    return false;
  }, []);

  const submitInterviewAnswer = useCallback(async (text) => {
    if (!presser) return null;
    try {
      const res = await api.interviewAnswer(presser.game_key, text, pointer);
      setPresser(res);
      return res;
    } catch (e) { toast('Could not send: ' + e.message); return null; }
  }, [presser, pointer, toast]);

  const skipInterview = useCallback(async () => {
    if (!presser) return null;
    try {
      const res = await api.interviewSkip(presser.game_key, pointer);
      setPresser(res);
      return res;
    } catch (e) { toast(e.message); return null; }
  }, [presser, pointer, toast]);

  // Close the presser once complete: jump straight to the Game Center and let the
  // week's coverage build in the background (no loading screen). The answers were
  // already on the record when the presser completed, so the backend's
  // post-presser pass is already running; we just pull its results in when ready.
  const closePresser = useCallback(async () => {
    const p = { ...pointer };
    setPresser(null);
    setActiveTab('gamecenter');
    refreshAfterPresser(p); // non-blocking: do not freeze the UI behind it
  }, [pointer, refreshAfterPresser]);

  // --- the Scan handoff (explicit; no auto-watch) --------------------------
  // Scan reads the save the Simulator wrote and registers/updates a dynasty in
  // the library. Used on the landing screen (pull in a dynasty) and from inside
  // the app (pull the latest week the Simulator advanced to).
  const scan = useCallback(async () => {
    if (scanBusyRef.current) return null;
    scanBusyRef.current = true;
    setScanning(true);
    try {
      const res = await api.scan();
      await refreshDynasties();
      // If we are already inside this dynasty, generate the new week behind the
      // overlay first, then swap the view (so tabs read from cache, instantly).
      if (enteredDynasty && res?.dynasty) {
        const p = { year: res.year, week: res.week };
        const sameWeek = p.year === pointer.year && p.week === pointer.week;
        const presserOwed = !!res.presser_owed;
        // A game just completed (presser owed): go STRAIGHT to the press conference
        // and defer ALL of this week's generation, even on a forward advance, until
        // the interview is done, so the coach's answers feed everything and there is
        // no loading screen before OR after the presser (closePresser builds it in
        // the background). Only a real week advance with no game to interview shows
        // the "Advancing to Week X" overlay. Every other same-week save change (a
        // Simulator roster / NIL / identity edit) is a QUIET refresh: the data reload
        // below (dynasty + budget + phone + feed) reflects it without a full
        // regeneration, and the week's existing media stands until the next advance.
        // The world-reaction engine still fires any texts/tweets a coach STATEMENT
        // warrants in the background, so a newsworthy edit is not silent.
        if (!presserOwed && !sameWeek) await generateWeek(p, { regenerate: false });
        setPointer(p);
        latestSeenRef.current = p;
        lastHashRef.current = res.dynasty.hash || null;
        setEnteredDynasty(res.dynasty);
        await loadDynasty(p.year, p.week);
        await reloadBudget();
        reloadKey.current += 1;
        setTick((t) => t + 1);
        // A new game just completed: open the post-game presser. The week's
        // coverage is deferred until it closes (closePresser), so the coach speaks
        // before anything is written and his answers feed all of it.
        await maybeOpenPresser(p);
      }
      toast(res?.dynasty ? `Scanned ${res.dynasty.team_name} (Week ${res.week})` : 'Scan complete');
      return res;
    } catch (e) {
      toast(e.message || 'No save found. Start a dynasty in the Simulator first.');
      return { present: false, error: e.message };
    } finally {
      setScanning(false);
      scanBusyRef.current = false;
    }
  }, [enteredDynasty, pointer, refreshDynasties, generateWeek, loadDynasty, reloadBudget, toast, maybeOpenPresser]);

  // Enter a dynasty from the library: point at its week, load it for theming,
  // generate the full week behind the overlay, then reveal the app. If a presser
  // is owed (the app was closed mid-presser, or a game was simulated while it was
  // closed), defer the week's generation until the interview is done, exactly like
  // the live flow, so the coach's answers feed it and the press conference comes
  // first instead of a loading screen.
  const selectDynasty = useCallback(async (id) => {
    try {
      const { dynasty: entry } = await api.selectDynasty(id);
      const p = { year: entry.year, week: entry.week };
      setPointer(p);
      latestSeenRef.current = p;
      lastHashRef.current = entry.hash || null;
      await loadDynasty(p.year, p.week);
      const { pending } = await api.interviewPending(p).catch(() => ({ pending: null }));
      if (!pending) await generateWeek(p);
      setEnteredDynasty(entry);
      await reloadBudget();
      reloadKey.current += 1;
      setTick((t) => t + 1);
      if (pending) await maybeOpenPresser(p); // presser first; closePresser builds the week
    } catch (e) {
      setLoading({ active: false, week: null, progress: 0, total: 0, module: null, subStep: null });
      toast('Could not open that dynasty: ' + e.message);
    }
  }, [loadDynasty, generateWeek, reloadBudget, toast, maybeOpenPresser]);

  const exitDynasty = useCallback(() => {
    setEnteredDynasty(null);
    setDynasty(null);
    refreshDynasties();
  }, [refreshDynasties]);

  // Live watch: while inside a dynasty, poll the save and react when the Simulator
  // changes it. Two triggers: a forward week advance, AND a same-week change (the
  // game was simulated without advancing, or a Simulator edit) detected by a new
  // content hash. Both route through scan(), which regenerates as needed and opens
  // the post-game presser when a game has just been played.
  useEffect(() => {
    if (!enteredDynasty) return undefined;
    let cancelled = false;
    let timer;
    const tick = async () => {
      try {
        const st = await api.state();
        const sv = st?.save;
        if (!cancelled && sv?.present && !scanBusyRef.current) {
          const advanced = sv.year > pointer.year
            || (sv.year === pointer.year && sv.week > pointer.week);
          const sameWeekChanged = sv.year === pointer.year && sv.week === pointer.week
            && sv.hash && sv.hash !== lastHashRef.current;
          if (advanced || sameWeekChanged) await scan();
        }
        // Coach actions the Simulator just drained (pending dropped): the save's
        // budget has been rewritten authoritatively. Pull it in, but do NOT
        // regenerate media (an NIL/recruiting spend changes the budget, not the
        // news). The content hash now excludes the budget, so this is the only
        // path that reacts to a spend. Also keeps the pending-actions chrome live.
        if (!cancelled && typeof st?.pending_actions === 'number') {
          if (st.pending_actions !== pendingRef.current) {
            if (st.pending_actions < pendingRef.current) reloadBudget();
            pendingRef.current = st.pending_actions;
            setPendingActions(st.pending_actions);
          }
        }
        // The world reacted to something the coach said: pull the fresh tweets
        // into the feed, the new articles into News / Top Stories (a tick bump
        // refetches the module-driven pages), and any texts people sent the coach
        // back into Messages (with their unread badges). First observation just
        // sets the baseline (no refresh).
        if (!cancelled && typeof st?.world_version === 'number') {
          if (worldVersionRef.current === null) {
            worldVersionRef.current = st.world_version;
          } else if (st.world_version !== worldVersionRef.current) {
            worldVersionRef.current = st.world_version;
            refreshFeed();
            refreshPhone();
            setTick((t) => t + 1);
          }
        }
      } catch { /* transient; keep watching */ }
      if (!cancelled) timer = setTimeout(tick, LIVE_POLL_MS);
    };
    timer = setTimeout(tick, LIVE_POLL_MS);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [enteredDynasty, pointer, scan, refreshFeed, refreshPhone, reloadBudget]);

  const value = {
    app: 'companion',
    config, dynasty, pointer, ready,
    mode, watcherActive, pendingActions,
    loading, toastMsg, toast,
    // dynasty library + the explicit Scan handoff
    dynastyLib, enteredDynasty, scanning, refreshDynasties, scan, selectDynasty, exitDynasty,
    phoneOpen, openPhone: () => setPhoneOpen(true), closePhone: () => setPhoneOpen(false),
    settingsOpen, openSettings, closeSettings,
    phoneContacts, phoneCategories, phoneThreads, appendThread, contactForName,
    unreadByContact, unreadTotal, markThreadRead,
    // social feed (the phone's second app)
    feedPosts, feedLikes, feedSeen, feedUnseen, refreshFeed, toggleFeedLike, markFeedSeen,
    activeChatId, setActiveChat: setActiveChatId, textPerson,
    activeTab, setActiveTab,
    // post-game press conference
    presser, submitInterviewAnswer, skipInterview, closePresser,
    budget, setBudget, reloadBudget,
    article, openArticle: (a) => setArticle(a), closeArticle: () => setArticle(null),
    goToWeek, scanNow: scan,
    reloadKey: tick, // bump to force pages to refetch
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
