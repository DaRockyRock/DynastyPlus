import { useState, useEffect, useCallback } from 'react';
import { useApp } from '../context/AppContext.jsx';
import { api } from '../lib/api.js';
import {
  PageHeader, SectionTitle, Button, EmptyState, WeekNav, ConfirmDialog,
  NewSeasonForm, SimStatusCard, Scoreboard, SimControlPanel, InboxDrainPanel,
} from '../components/index.js';

// The Simulator's season driver: start a season, then step week to week. Each
// advance drains any companion coach actions, sims the FBS slate, and rewrites
// the save the Dynasty+ companion watches. Composed entirely from the library.
export default function SimDashboardPage() {
  const {
    sim, simBusy, simActive, startSeason, simulateGame, advanceSim, resetSim, deleteDynasty,
    pointer, reloadKey, fbsTeams, team, teamBusy, setUserTeam,
  } = useApp();

  const [viewWeek, setViewWeek] = useState(1);
  const [games, setGames] = useState([]);
  const [userGame, setUserGame] = useState(null);
  const [pending, setPending] = useState([]);
  const [override, setOverride] = useState({ enabled: false, value: { user_score: '', opp_score: '' } });
  const [confirmDelete, setConfirmDelete] = useState(false);

  const year = sim?.year;
  const week = sim?.week;
  const weeksTotal = sim?.weeks_total || 12;

  useEffect(() => { if (week) setViewWeek(week); }, [week, year]);

  const loadBoard = useCallback(async (w) => {
    if (!simActive || !w) return;
    try { const r = await api.simScoreboard({ year, week: w }); setGames(r.games || []); }
    catch { setGames([]); }
  }, [simActive, year]);

  useEffect(() => { loadBoard(viewWeek); }, [viewWeek, loadBoard, week]);

  // Coach actions queued by the companion, applied on the next advance.
  const loadInbox = useCallback(async () => {
    try { const r = await api.inbox({ year }); setPending(r.pending || []); }
    catch { setPending([]); }
  }, [year]);
  useEffect(() => { if (simActive) loadInbox(); }, [simActive, loadInbox, reloadKey]);

  useEffect(() => {
    if (!simActive || !week) { setUserGame(null); return; }
    api.simScoreboard({ year, week }).then((r) => {
      const row = (r.games || []).find((g) => g.user);
      if (!row) { setUserGame(null); return; }
      const home = row.home.is_user;
      setUserGame({ team: home ? row.home : row.away, opponent: home ? row.away : row.home, home, week });
    }).catch(() => setUserGame(null));
  }, [simActive, year, week]);

  const _override = () => {
    const v = override.value;
    return override.enabled && v.user_score !== '' && v.opp_score !== ''
      ? { user_score: Number(v.user_score), opp_score: Number(v.opp_score) } : null;
  };
  const onSimulateGame = async () => {
    try {
      await simulateGame(_override());
      setOverride({ enabled: false, value: { user_score: '', opp_score: '' } });
    } catch { /* toast handled in context */ }
  };
  const onAdvance = async () => {
    try {
      await advanceSim(_override());
      setOverride({ enabled: false, value: { user_score: '', opp_score: '' } });
    } catch { /* toast handled in context */ }
  };
  const onDelete = async () => {
    try { await deleteDynasty(); } catch { /* toast handled in context */ }
    finally { setConfirmDelete(false); }
  };

  // Destructive "start from scratch" affordance, available whether or not a
  // season is active (stale data often lingers after a Reset).
  const deleteAction = <Button onClick={() => setConfirmDelete(true)} disabled={simBusy}>Delete Dynasty</Button>;
  const deleteConfirm = (
    <ConfirmDialog
      open={confirmDelete}
      title="Delete Dynasty"
      confirmLabel="Delete Everything"
      danger
      busy={simBusy}
      onClose={() => setConfirmDelete(false)}
      onConfirm={onDelete}
    >
      This permanently wipes every simulated season and all generated media, archives,
      budget, and phone, feed, and news state, plus your team customization. Both apps
      start completely from scratch. This cannot be undone.
    </ConfirmDialog>
  );

  if (sim && !sim.has_seed) {
    return <EmptyState>Build the FBS league seed first: run scripts/build_league_seed.py</EmptyState>;
  }

  if (!simActive) {
    return (
      <>
        <PageHeader
          title="Season"
          sub="Start and step through a modeled CFB 27 season."
          actions={deleteAction}
        />
        <NewSeasonForm
          defaultYear={(sim?.year) || pointer.year}
          busy={simBusy}
          onStart={startSeason}
          teams={fbsTeams}
          team={team?.name || ''}
          onSelectTeam={setUserTeam}
          teamBusy={teamBusy}
        />
        {deleteConfirm}
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Season"
        sub={`${sim.user_team} • ${sim.user_record} (${sim.user_conf_record})`}
        actions={(
          <>
            <Button onClick={resetSim} disabled={simBusy}>Reset Season</Button>
            {deleteAction}
          </>
        )}
      />
      <SimStatusCard status={sim} />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, alignItems: 'start', margin: '18px 0' }}>
        <SimControlPanel
          week={sim.week}
          userGame={userGame}
          simmed={!!sim.current_week_simmed}
          override={override}
          onToggleOverride={(e) => setOverride((o) => ({ ...o, enabled: e }))}
          onChangeOverride={(value) => setOverride((o) => ({ ...o, value }))}
          onSimulateGame={onSimulateGame}
          onAdvance={onAdvance}
          busy={simBusy}
        />
        <InboxDrainPanel actions={pending} />
      </div>

      <Scoreboard
        week={viewWeek}
        games={games}
        right={(
          <WeekNav
            week={viewWeek}
            onPrev={() => setViewWeek((w) => Math.max(1, w - 1))}
            onNext={() => setViewWeek((w) => Math.min(weeksTotal, w + 1))}
          />
        )}
      />
      {deleteConfirm}
    </>
  );
}
