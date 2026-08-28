import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { api } from '../../lib/api.js';
import Button from '../ui/Button.jsx';
import PanelCard from '../ui/PanelCard.jsx';
import Callout from '../ui/Callout.jsx';
import NumberStepper from '../ui/NumberStepper.jsx';
import ToggleSwitch from '../ui/ToggleSwitch.jsx';
import SegmentedControl from '../ui/SegmentedControl.jsx';
import Select from '../ui/Select.jsx';
import TextInput from '../ui/TextInput.jsx';
import ByeTierEditor from './ByeTierEditor.jsx';
import RoundSiteEditor from './RoundSiteEditor.jsx';
import PlayoffBracket from './PlayoffBracket.jsx';
import PlayoffSelectionSummary from './PlayoffSelectionSummary.jsx';
import PlayoffAutomationToggle from './PlayoffAutomationToggle.jsx';
import PlayoffOffState from './PlayoffOffState.jsx';
import StadiumSelect from './StadiumSelect.jsx';

// The playoff format studio: every rule of the dynasty's postseason in one
// editor, with a live preview bracket seeded from the current rankings. Opens
// as a full-screen overlay (from the CFP page) or embedded in the Customize
// studio. Data flows through /api/playoff/*; stories can inject initialData
// and a previewFn instead.
//
// The preview never advances anyone: it is this week's field dropped into the
// draft format, exactly what backend/playoff.build_bracket returns.

const FIELD_NOTES = {
  1: 'Poll era: no games are played, the top-ranked team is crowned champion.',
  2: 'BCS era: the top two teams meet in a single national championship game.',
};

function suggestByes(teams) {
  if (teams <= 2) return [];
  const full = 2 ** Math.ceil(Math.log2(teams));
  return full - teams > 0 ? [{ rounds: 1, teams: full - teams }] : [];
}

export default function PlayoffFormatEditor({
  open = true,
  onClose,
  onSaved,
  embedded = false,
  toast,
  pointer,
  initialData = null,
  previewFn = null,
}) {
  const [data, setData] = useState(initialData);
  const [draft, setDraft] = useState(initialData?.format || null);
  const [stadiums, setStadiums] = useState(initialData?.stadiums || []);
  const [preview, setPreview] = useState(null);
  const [problems, setProblems] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [togglingEnabled, setTogglingEnabled] = useState(false);
  const previewSeq = useRef(0);

  const notify = toast || (() => {});

  useEffect(() => {
    if (!open || data) return undefined;
    let alive = true;
    api.playoffFormat()
      .then((res) => {
        if (!alive) return;
        setData(res);
        setDraft(res.format);
      })
      .catch((e) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [open, data]);

  // The game's real stadium list for the neutral-site pickers, fetched once
  // per open independently of the format load (empty when no real save is
  // readable, which flips the pickers to free-text venue/city).
  useEffect(() => {
    if (!open || stadiums.length) return undefined;
    let alive = true;
    api.playoffStadiums()
      .then((res) => { if (alive && res.available) setStadiums(res.stadiums); })
      .catch(() => {});
    return () => { alive = false; };
  }, [open, stadiums.length]);

  // Live preview, debounced so steppers do not spam the backend.
  useEffect(() => {
    if (!open || !draft) return undefined;
    const seq = previewSeq.current + 1;
    previewSeq.current = seq;
    const t = setTimeout(() => {
      const run = previewFn || ((fmt) => api.playoffPreview(fmt, pointer || {}));
      run(draft)
        .then((res) => {
          if (previewSeq.current !== seq) return;
          setPreview(res.bracket || null);
          setProblems(res.problems || []);
        })
        .catch((e) => { if (previewSeq.current === seq) setProblems([e.message]); });
    }, 350);
    return () => clearTimeout(t);
  }, [open, draft, previewFn, pointer]);

  const patch = useCallback((changes) => setDraft((d) => ({ ...d, ...changes })), []);
  const patchSites = useCallback((changes) => setDraft((d) => ({ ...d, sites: { ...d.sites, ...changes } })), []);
  const patchDq = useCallback((changes) => setDraft((d) => ({ ...d, disqualify: { ...d.disqualify, ...changes } })), []);
  const patchLimits = useCallback((changes) => setDraft((d) => ({ ...d, conference_limits: { ...d.conference_limits, ...changes } })), []);

  const byeTotal = useMemo(
    () => (draft?.byes || []).reduce((sum, t) => sum + t.teams, 0),
    [draft],
  );

  const previewRounds = preview?.rounds || [];
  const editableRounds = previewRounds.slice(0, Math.max(0, previewRounds.length - 1));

  const save = async () => {
    setSaving(true);
    try {
      await api.savePlayoffFormat(draft);
      notify('Playoff format saved');
      onSaved?.();
    } catch (e) {
      notify('Save failed: ' + e.message);
    } finally {
      setSaving(false);
    }
  };

  const reset = async () => {
    try {
      const res = await api.resetPlayoffFormat();
      setDraft(res.format);
      setData((d) => (d ? { ...d, format: res.format, customized: false } : d));
      notify('Playoff format reset to the real CFP');
    } catch (e) {
      notify('Reset failed: ' + e.message);
    }
  };

  const toggleEnabled = async (next) => {
    setTogglingEnabled(true);
    try {
      await api.setPlayoffConfig({ enabled: next });
      setData((d) => (d ? { ...d, enabled: next } : d));
      notify(next
        ? 'Custom playoff bracket on'
        : 'Custom playoff bracket off. CFB 27 runs its native playoff.');
    } catch (e) {
      notify('Could not change the setting: ' + e.message);
    } finally {
      setTogglingEnabled(false);
    }
  };

  if (!open) return null;

  // Off (the opt-in default): the whole editor collapses to the off-state
  // hero, the switch front and center, so it is unmistakable that CFB 27 is
  // running its own playoff and where to turn the tool back on.
  const off = data ? data.enabled === false : false;

  const body = error ? (
    <Callout tone="warn" title="Could not load the playoff format">{error}</Callout>
  ) : off ? (
    <PlayoffOffState onEnable={() => toggleEnabled(true)} busy={togglingEnabled} />
  ) : !draft ? (
    <div className="empty-state">Loading playoff format...</div>
  ) : (
    <div className="pfe-layout">
      <div className="pfe-controls">
        {data?.enabled !== undefined && (
          <PlayoffAutomationToggle
            enabled={!!data.enabled}
            onChange={toggleEnabled}
            busy={togglingEnabled}
          />
        )}
        <PanelCard title="Field">
          <div className="pfe-row">
            <span className="pfe-row-label">
              Playoff teams
              <span className="pfe-row-sub">From a 1-team poll champion to a 128-team open bracket</span>
            </span>
            <NumberStepper value={draft.teams} min={1} max={128} onChange={(teams) => patch({ teams })} />
          </div>
          {FIELD_NOTES[draft.teams] && <p className="pb-note">{FIELD_NOTES[draft.teams]}</p>}
          {draft.teams > 2 && (
            <div className="pfe-row">
              <span className="pfe-row-label">
                Reseed after every round
                <span className="pfe-row-sub">Matchups re-pair each round: the best remaining seed plays the worst remaining, NFL style</span>
              </span>
              <ToggleSwitch checked={!!draft.reseed} onChange={(v) => patch({ reseed: v })} />
            </div>
          )}
        </PanelCard>

        {draft.teams > 2 && (
          <PanelCard title="Byes" right={byeTotal ? `${byeTotal} teams` : 'None'}>
            <ByeTierEditor tiers={draft.byes} maxTeams={draft.teams - 1} onChange={(byes) => patch({ byes })} />
            <div className="pfe-row" style={{ marginTop: 10 }}>
              <span className="pfe-row-label">
                Bye selection
                <span className="pfe-row-sub">Who earns the protected seeds</span>
              </span>
              <SegmentedControl
                options={[
                  { value: 'seeding', label: 'By Seeding' },
                  { value: 'champs', label: 'Top Champs' },
                ]}
                value={draft.bye_selection}
                onChange={(bye_selection) => patch({ bye_selection })}
              />
            </div>
            {problems.length > 0 && (
              <button type="button" className="pfe-inline-btn" onClick={() => patch({ byes: suggestByes(draft.teams) })}>
                Fix byes automatically
              </button>
            )}
          </PanelCard>
        )}

        {draft.teams > 1 && (
          <PanelCard title="Automatic Bids">
            <div className="pfe-row">
              <span className="pfe-row-label">
                Conference champion auto-bids
                <span className="pfe-row-sub">The best-ranked champions are guaranteed a spot</span>
              </span>
              <NumberStepper
                value={draft.auto_bids?.champions || 0}
                min={0}
                max={10}
                onChange={(champions) => patch({ auto_bids: { champions } })}
              />
            </div>
            <div className="pfe-row">
              <span className="pfe-row-label">
                Notre Dame access rule
                <span className="pfe-row-sub">A top-{draft.teams} Notre Dame is guaranteed a bid as an independent</span>
              </span>
              <ToggleSwitch checked={!!draft.notre_dame_rule} onChange={(v) => patch({ notre_dame_rule: v })} />
            </div>
          </PanelCard>
        )}

        {draft.teams > 1 && (
          <PanelCard title="Conference Limits">
            <div className="pfe-row">
              <span className="pfe-row-label">
                Cap teams per conference
                <span className="pfe-row-sub">No conference can send more than this many teams</span>
              </span>
              <ToggleSwitch
                checked={draft.conference_limits?.max_per_conf != null}
                onChange={(v) => patchLimits({ max_per_conf: v ? 2 : null })}
              />
            </div>
            {draft.conference_limits?.max_per_conf != null && (
              <div className="pfe-row">
                <span className="pfe-row-label">Maximum per conference</span>
                <NumberStepper
                  value={draft.conference_limits.max_per_conf}
                  min={1}
                  max={draft.teams}
                  onChange={(max_per_conf) => patchLimits({ max_per_conf })}
                />
              </div>
            )}
            <div className="pfe-row">
              <span className="pfe-row-label">
                Guaranteed bids per conference
                <span className="pfe-row-sub">Every conference gets at least this many teams (0 for none)</span>
              </span>
              <NumberStepper
                value={draft.conference_limits?.min_per_conf || 0}
                min={0}
                max={draft.teams}
                onChange={(min_per_conf) => patchLimits({ min_per_conf })}
              />
            </div>
          </PanelCard>
        )}

        {draft.teams > 1 && (
          <PanelCard title="Disqualifiers">
            <div className="pfe-stack">
              <div className="pfe-row">
                <span className="pfe-row-label">
                  Cap regular season losses
                  <span className="pfe-row-sub">Teams over the cap are out, no matter their ranking</span>
                </span>
                <ToggleSwitch
                  checked={draft.disqualify?.max_losses != null}
                  onChange={(v) => patchDq({ max_losses: v ? 3 : null })}
                />
              </div>
              {draft.disqualify?.max_losses != null && (
                <div className="pfe-row">
                  <span className="pfe-row-label">Maximum losses</span>
                  <NumberStepper
                    value={draft.disqualify.max_losses}
                    min={0}
                    max={11}
                    onChange={(max_losses) => patchDq({ max_losses })}
                  />
                </div>
              )}
              <div className="pfe-row">
                <span className="pfe-row-label">Losing conference record disqualifies</span>
                <ToggleSwitch checked={!!draft.disqualify?.losing_conf_record} onChange={(v) => patchDq({ losing_conf_record: v })} />
              </div>
              <div className="pfe-row">
                <span className="pfe-row-label">Rivalry week loss disqualifies</span>
                <ToggleSwitch checked={!!draft.disqualify?.rivalry_week_loss} onChange={(v) => patchDq({ rivalry_week_loss: v })} />
              </div>
              <div className="pfe-row">
                <span className="pfe-row-label">Committee top 25 only</span>
                <ToggleSwitch checked={!!draft.disqualify?.ranked_only} onChange={(v) => patchDq({ ranked_only: v })} />
              </div>
              <div className="pfe-row">
                <span className="pfe-row-label">Conference champions only</span>
                <ToggleSwitch checked={!!draft.disqualify?.champions_only} onChange={(v) => patchDq({ champions_only: v })} />
              </div>
            </div>
          </PanelCard>
        )}

        <PanelCard title="Game Sites">
          {editableRounds.length === 0 && draft.teams > 1 && (
            <p className="pb-note">Round sites appear once the bracket closes (fix any structure problems above).</p>
          )}
          <div className="pfe-stack">
            {editableRounds.map((rnd, i) => (
              <RoundSiteEditor
                key={rnd.round}
                name={rnd.name}
                games={rnd.games}
                bowls={data?.bowls || []}
                stadiums={stadiums}
                config={draft.sites?.rounds?.[i] || {}}
                onChange={(rc) => {
                  const rounds = [...(draft.sites?.rounds || [])];
                  while (rounds.length <= i) rounds.push({});
                  rounds[i] = rc;
                  patchSites({ rounds });
                }}
              />
            ))}
            {draft.teams > 1 && (
              <div>
                <div className="pfe-row">
                  <span className="pfe-row-label">National Championship</span>
                  <SegmentedControl
                    options={[
                      { value: 'neutral', label: 'Neutral Site' },
                      { value: 'bowls', label: 'Bowl' },
                    ]}
                    value={draft.sites?.championship?.mode || 'neutral'}
                    onChange={(mode) => patchSites({ championship: { ...draft.sites?.championship, mode } })}
                  />
                </div>
                {(draft.sites?.championship?.mode || 'neutral') === 'bowls' ? (
                  <div className="pfe-game-row">
                    <Select
                      options={[
                        { value: '', label: 'Top available bowl' },
                        ...(data?.bowls || []).map((b) => ({ value: b.key, label: b.name })),
                      ]}
                      value={draft.sites?.championship?.bowl || ''}
                      onValueChange={(bowl) => patchSites({ championship: { ...draft.sites?.championship, bowl: bowl || null } })}
                    />
                  </div>
                ) : stadiums.length ? (
                  <div className="pfe-game-row">
                    <StadiumSelect
                      stadiums={stadiums}
                      value={draft.sites?.championship?.stadium}
                      placeholder="Pick the title-game stadium"
                      onPick={(s) => patchSites({
                        championship: {
                          ...draft.sites?.championship,
                          stadium: s ? s.index : null,
                          venue: s ? s.name : '',
                          city: s ? (s.city || '') : '',
                        },
                      })}
                    />
                  </div>
                ) : (
                  <div className="pfe-game-row">
                    <TextInput
                      placeholder="Venue"
                      value={draft.sites?.championship?.venue || ''}
                      onValueChange={(venue) => patchSites({ championship: { ...draft.sites?.championship, venue } })}
                    />
                    <TextInput
                      placeholder="City"
                      value={draft.sites?.championship?.city || ''}
                      onValueChange={(city) => patchSites({ championship: { ...draft.sites?.championship, city } })}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        </PanelCard>
      </div>

      <div className="pfe-preview">
        {problems.map((p, i) => (
          <Callout key={i} tone="warn" title="This format cannot be built yet">{p}</Callout>
        ))}
        {preview && <PlayoffBracket bracket={preview} championLabel="National Champion" />}
        {preview && (
          <PanelCard title="Selection" flush={false} className="pfe-selection">
            <PlayoffSelectionSummary selection={preview.selection} />
          </PanelCard>
        )}
      </div>
    </div>
  );

  if (embedded) {
    // Off: only the hero renders, no page header or format actions.
    return (
      <div className="pfe-embedded">
        {!off && (
          <div className="pfe-head" style={{ marginBottom: 14 }}>
            <h1 style={{ fontSize: 26 }}>Playoff Format</h1>
            <Button variant="regen" onClick={reset}>Reset to CFP</Button>
            <Button variant="accent" onClick={save} disabled={!draft || problems.length > 0} spinning={saving}>
              {saving ? 'Saving' : 'Save Format'}
            </Button>
          </div>
        )}
        {body}
      </div>
    );
  }

  return (
    <div className="pfe-overlay">
      <div className="pfe-head">
        <h1>Playoff Format</h1>
        {/* off: the hero is the only content; keep just the way out */}
        {!off && <Button variant="regen" onClick={reset}>Reset to CFP</Button>}
        <Button onClick={onClose}>Cancel</Button>
        {!off && (
          <Button variant="accent" onClick={save} disabled={!draft || problems.length > 0} spinning={saving}>
            {saving ? 'Saving' : 'Save Format'}
          </Button>
        )}
      </div>
      {body}
    </div>
  );
}
