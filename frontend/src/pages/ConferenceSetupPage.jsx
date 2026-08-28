import { useState, useEffect, useCallback, useMemo } from 'react';
import { useApp } from '../context/AppContext.jsx';
import { api } from '../lib/api.js';
import { registerConferences } from '../lib/conferences.js';
import {
  GameScreen, EmptyState, Skeleton, Button, ConfirmDialog, ConferenceLogo,
  ConferenceIdentityCard, ConferenceMemberList, TeamMovePicker, DivisionEditor,
  RivalryEditor, SaveProgressOverlay, ModToolsPanel,
} from '../components/index.js';

// The Conference Setup editor. Reads the setup from the active dynasty's save,
// lets the user rename conferences, realign teams, set divisions, rivalries,
// and logos, and on Save writes it straight back into that save in place
// (names any week, membership in the offseason) and rebuilds the logo mod. The
// page owns all state; the components are presentational.
function eq(a, b) { return JSON.stringify(a) === JSON.stringify(b); }

export default function ConferenceSetupPage() {
  const { toast } = useApp();
  const [state, setState] = useState(null);   // server truth (last saved)
  const [draft, setDraft] = useState(null);    // in-memory edits (list of conferences)
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeId, setActiveId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveSteps, setSaveSteps] = useState(null);  // progress overlay steps
  const [moving, setMoving] = useState(null);   // team name being moved
  const [confirmReset, setConfirmReset] = useState(false);
  const [modTools, setModTools] = useState(null);      // MMC tools detection
  const [modBusy, setModBusy] = useState(false);
  const [lastExport, setLastExport] = useState(null);  // last .fbmod export report
  const [historicLogos, setHistoricLogos] = useState({});  // conf key -> classic marks

  const refreshModTools = useCallback(async () => {
    try { setModTools(await api.modToolsStatus()); } catch { /* ignore */ }
  }, []);

  const locateModTools = useCallback(async (path) => {
    setModBusy(true);
    try {
      setModTools(await api.setModToolsPath(path));
      toast('MMC Modding Tools found');
    } catch (e) {
      toast(e.message);
    } finally {
      setModBusy(false);
    }
  }, [toast]);

  const openModManager = useCallback(async () => {
    try { await api.openModManager(); } catch (e) { toast(e.message); }
  }, [toast]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.conferenceSetup();
      setState(res);
      setDraft(res.conferences || []);
      registerConferences(res.conferences || []);
      setActiveId((prev) => prev || (res.conferences?.[0]?.id ?? null));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); refreshModTools(); }, [load, refreshModTools]);

  useEffect(() => {
    let live = true;
    api.historicConfLogos()
      .then((res) => { if (live) setHistoricLogos(res.logos || {}); })
      .catch(() => { /* picker just stays hidden */ });
    return () => { live = false; };
  }, []);

  const teamsByName = useMemo(
    () => Object.fromEntries((state?.teams || []).map((t) => [t.name, t])),
    [state],
  );
  const dirty = useMemo(
    () => !!state && !eq(draft, state.conferences),
    [draft, state],
  );

  const active = draft?.find((c) => c.id === activeId) || null;

  // --- draft mutations -------------------------------------------------------
  const patchConf = (id, patch) =>
    setDraft((d) => d.map((c) => (c.id === id ? { ...c, ...patch } : c)));

  const moveTeam = ({ toId, division }) => {
    const team = moving;
    setMoving(null);
    if (!team) return;
    setDraft((d) => d.map((c) => {
      if (c.id === active.id) {
        return {
          ...c,
          teams: c.teams.filter((t) => t !== team),
          divisions: (c.divisions || []).map((dv) => ({ ...dv, teams: dv.teams.filter((t) => t !== team) })),
        };
      }
      if (c.id === toId) {
        const divisions = (c.divisions || []).map((dv, i) => {
          const target = division ? dv.name === division : i === 0;
          return target ? { ...dv, teams: [...dv.teams, team] } : dv;
        });
        return { ...c, teams: [...c.teams, team], divisions };
      }
      return c;
    }));
  };

  const swapDivision = (teamName) => {
    setDraft((d) => d.map((c) => {
      if (c.id !== active.id || (c.divisions || []).length < 2) return c;
      const from = c.divisions.findIndex((dv) => dv.teams.includes(teamName));
      const to = (from + 1) % c.divisions.length;
      const divisions = c.divisions.map((dv, i) => {
        if (i === from) return { ...dv, teams: dv.teams.filter((t) => t !== teamName) };
        if (i === to) return { ...dv, teams: [...dv.teams, teamName] };
        return dv;
      });
      return { ...c, divisions };
    }));
  };

  const renameDivision = (row, name) =>
    setDraft((d) => d.map((c) => (c.id === active.id
      ? { ...c, divisions: c.divisions.map((dv) => (dv.row === row ? { ...dv, name } : dv)) }
      : c)));

  // Any conference carrying an uploaded logo drives the logo-mod export. We
  // export whenever one is present (not only when it changed) so the mod file
  // can never go stale, e.g. if the logo was set outside this session.
  const hasCustomLogos = useMemo(
    () => (draft || []).some((c) => {
      const logo = c.logo || '';
      return logo.startsWith('/uploads/') || logo.startsWith('/game-assets/conferences/historic/');
    }),
    [draft],
  );

  // --- save: write to the save, then export the logo mod if a logo is set ---
  const save = async () => {
    const exportStep = { label: 'Exporting the logo mod for the MMC Mod Manager', status: 'pending' };
    const steps = [
      { label: 'Writing changes into your dynasty save', status: 'active' },
      ...(hasCustomLogos ? [exportStep] : []),
    ];
    setSaveSteps(steps);
    setSaving(true);
    try {
      // phase 1: persist + patch the save in place (names, titles, moves)
      const res = await api.saveConferenceSetup(draft);
      setState(res);
      setDraft(res.conferences || []);
      registerConferences(res.conferences || []);
      const a = res.last_apply || {};

      // phase 2: export the .fbmod so the mod library reflects the current
      // logos. This is optional: the conference edits are already in the save
      // from phase 1, so a failed export skips only the logo textures.
      let mod = null;
      if (res.has_custom_logos) {
        setSaveSteps([{ ...steps[0], status: 'done' }, { ...exportStep, status: 'active' }]);
        try { mod = await api.exportConferenceMod(); }
        catch (e) { mod = { error: e.message }; }
      }
      setSaveSteps(steps.map((s) => (
        s.label === exportStep.label && mod && mod.error
          ? { ...s, status: 'skipped' }
          : { ...s, status: 'done' }
      )));

      // report: names/moves are in the save now; the logo note is optional
      if (a.saved_to) toast('Saved into your dynasty. Load the save in CFB 27 to see your changes.');
      else toast('Conference setup saved');
      (a.pending || []).forEach((p) => toast(p));
      if (mod && !mod.error) {
        setLastExport(mod);
        if (mod.modtools) setModTools(mod.modtools);
        toast(mod.installed_to
          ? 'Logo mod exported into the MMC Mod Manager. Apply and launch from there to see your logos.'
          : 'Logo mod exported. Install the MMC Modding Tools to play with it.');
        (mod.skipped || []).forEach((s) => toast(s));
      } else if (mod && mod.error) {
        // the backend returns a complete, user-facing sentence for the expected
        // "image tools unavailable" case; show it as-is (the save still landed)
        toast(mod.error);
      }
    } catch (e) {
      toast('Save failed: ' + e.message);
    } finally {
      setSaving(false);
      setSaveSteps(null);
    }
  };

  const doReset = async () => {
    setConfirmReset(false);
    try {
      const res = await api.resetConferenceSetup();
      setState(res);
      setDraft(res.conferences || []);
      registerConferences(res.conferences || []);
      toast('Reverted to the game save');
    } catch (e) {
      toast('Reset failed: ' + e.message);
    }
  };

  // --- render ----------------------------------------------------------------
  if (loading) {
    return <GameScreen><Skeleton height={420} /></GameScreen>;
  }
  if (error) {
    return <GameScreen><EmptyState>Could not load conference setup: {error}</EmptyState></GameScreen>;
  }
  if (!state?.available) {
    const reason = state?.apply_gate?.reason;
    return (
      <GameScreen heroTitle="Conference Setup">
        <EmptyState>
          {reason && reason !== 'No CFB 27 save was found.'
            ? `${reason} Scan a dynasty first, or try another save.`
            : 'No CFB 27 save was found, so there are no conferences to edit yet. Scan a dynasty first.'}
        </EmptyState>
      </GameScreen>
    );
  }

  const menu = draft.map((c) => ({
    id: c.id,
    label: c.name,
    sub: `${c.teams.length} team${c.teams.length === 1 ? '' : 's'}`,
    icon: <ConferenceLogo name={c.name} size={22} plate={false} />,
  }));

  return (
    <GameScreen
      menu={menu}
      active={activeId}
      onSelect={setActiveId}
    >
      {/* Only surfaces when a custom logo is set AND the mod tools are not
          ready yet, so it guides setup but stops nagging once mods can load. */}
      {hasCustomLogos && (!modTools || !modTools.ready) && (
        <ModToolsPanel
          status={modTools}
          onLocate={locateModTools}
          onOpenManager={openModManager}
          onRefresh={refreshModTools}
          exportResult={lastExport}
          busy={modBusy || saving}
        />
      )}
      {active ? (
        <>
          <ConferenceIdentityCard
            conf={active}
            onChange={(next) => patchConf(active.id, next)}
            historicLogos={historicLogos[active.key] || []}
          />
          <ConferenceMemberList conf={active} teamsByName={teamsByName} onMove={setMoving} />
          {(active.divisions || []).length >= 2 && (
            <DivisionEditor conf={active} teamsByName={teamsByName} onRename={renameDivision} onSwap={swapDivision} />
          )}
          <RivalryEditor conf={active} onChange={(rivalries) => patchConf(active.id, { rivalries })} />
        </>
      ) : (
        <EmptyState>Select a conference from the rail.</EmptyState>
      )}

      {/* Only surfaces when there are unsaved edits; a fully saved page shows no
          bar (no persistent "Saved to your dynasty" footer). */}
      {dirty && (
        <div className="cs-savebar dirty">
          <span className="cs-savebar-note">Unsaved changes</span>
          <span className="cs-savebar-actions">
            <Button onClick={() => setConfirmReset(true)} disabled={saving}>Reset</Button>
            <Button variant="accent" spinning={saving} disabled={saving} onClick={save}>
              {saving ? 'Saving...' : 'Save'}
            </Button>
          </span>
        </div>
      )}

      <TeamMovePicker
        open={!!moving}
        team={moving}
        teamsByName={teamsByName}
        conferences={draft}
        fromId={active?.id}
        onMove={moveTeam}
        onClose={() => setMoving(null)}
      />
      <ConfirmDialog
        open={confirmReset}
        title="Reset to the game save?"
        confirmLabel="Reset"
        danger
        onConfirm={doReset}
        onClose={() => setConfirmReset(false)}
      >
        This discards every conference edit and reverts to the alignment in the current save.
      </ConfirmDialog>

      <SaveProgressOverlay open={saving && !!saveSteps} steps={saveSteps || []} />
    </GameScreen>
  );
}
