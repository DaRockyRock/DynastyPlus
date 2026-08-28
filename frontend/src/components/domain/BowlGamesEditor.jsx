import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../../lib/api.js';
import Button from '../ui/Button.jsx';
import Callout from '../ui/Callout.jsx';
import EmptyState from '../ui/EmptyState.jsx';
import BowlGameCard from './BowlGameCard.jsx';

const DEFAULT_API = { load: api.bowlGames, apply: api.applyBowlGames };

// Complete yearly bowl editor. Stories inject
// data and API stubs so every state is reviewable without a live CFB save.
export default function BowlGamesEditor({ toast, initialData = null, apiFns = DEFAULT_API }) {
  const [data, setData] = useState(initialData);
  const [drafts, setDrafts] = useState(initialData?.assignments || []);
  const [loading, setLoading] = useState(!initialData);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const adopt = useCallback((next) => {
    setData(next);
    setDrafts(next?.assignments || []);
    setError(null);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try { adopt(await apiFns.load()); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }, [adopt, apiFns]);

  useEffect(() => {
    if (!initialData) load();
  }, [initialData, load]);

  const original = useMemo(
    () => new Map((data?.assignments || []).map((item) => [item.record, item])),
    [data],
  );
  const draftMap = useMemo(() => new Map(drafts.map((item) => [item.record, item])), [drafts]);
  const dirtyRecords = useMemo(() => new Set(drafts.filter((item) => {
    const before = original.get(item.record);
    return !before || before.away_row !== item.away_row || before.home_row !== item.home_row;
  }).map((item) => item.record)), [drafts, original]);

  const change = useCallback((record, side, row) => {
    setDrafts((current) => {
      const target = current.find((item) => item.record === record);
      const previous = target?.[side];
      return current.map((item) => {
        if (item.record === record) return { ...item, [side]: row };
        if (item.away_row === row) return { ...item, away_row: previous };
        if (item.home_row === row) return { ...item, home_row: previous };
        return item;
      });
    });
  }, []);

  const runApply = useCallback(async ({ auto = false } = {}) => {
    setBusy(true);
    try {
      const next = await apiFns.apply(auto ? { auto: true } : { assignments: drafts });
      adopt(next);
      toast?.(next.written
        ? 'Bowl schedule written. Reload the dynasty in CFB 27.'
        : 'Bowl schedule is already up to date.');
    } catch (err) {
      setError(err.message);
      toast?.('Could not update the bowl schedule: ' + err.message);
    } finally {
      setBusy(false);
    }
  }, [adopt, apiFns, drafts, toast]);

  if (loading) return <EmptyState>Loading the bowl schedule...</EmptyState>;
  if (!data?.available) {
    return <EmptyState>{data?.reason || 'The postseason field is not set yet.'}</EmptyState>;
  }

  const marquee = data.games.filter((game) => game.ny6);
  const standard = data.games.filter((game) => !game.ny6);
  const renderCards = (games) => games.map((game) => (
    <BowlGameCard
      key={game.record}
      game={game}
      teams={data.teams}
      assignment={draftMap.get(game.record)}
      editable={data.editable && !busy}
      dirty={dirtyRecords.has(game.record)}
      onChange={(side, row) => change(game.record, side, row)}
    />
  ));

  return (
    <section className="bowl-games-editor">
      <header className="bge-hero">
        <div className="bge-kicker">{data.year} Postseason</div>
        <div className="bge-title-row">
          <div>
            <h1>Bowl Games</h1>
            <p>Every nonplayoff bowl, balanced around your custom field and ready for final selection.</p>
          </div>
          <div className="bge-actions">
            <Button onClick={() => runApply({ auto: true })} disabled={busy || !data.editable}>
              Auto Assign All
            </Button>
            <Button variant="accent" onClick={() => runApply()} disabled={busy || !data.editable || (!dirtyRecords.size && data.applied)}>
              {busy ? 'Updating...' : 'Update Dynasty File'}
            </Button>
          </div>
        </div>
        <div className="bge-summary">
          <span><strong>{data.summary.bowls}</strong> bowl games</span>
          <span><strong>{data.summary.ny6}</strong> available NY6</span>
          <span><strong>{data.summary.teams}</strong> selected teams</span>
          <span><strong>{data.summary.locked}</strong> final games</span>
          {!!data.summary.inactive && <span><strong>{data.summary.inactive}</strong> inactive for this field size</span>}
          <span className={`bge-sync${data.applied && !dirtyRecords.size ? ' ready' : ''}`}>
            {data.applied && !dirtyRecords.size ? 'Save matches this schedule' : 'Changes waiting'}
          </span>
        </div>
      </header>
      {error && <Callout tone="warn" title="Bowl schedule needs attention">{error}</Callout>}
      {!data.editable && (
        <Callout title="This bowl season is complete">Final bowl games stay visible, but completed matchups cannot be changed.</Callout>
      )}
      {!!marquee.length && (
        <section className="bge-section bge-marquee">
          <header><span>Marquee Bowls</span><small>Unused by your custom playoff</small></header>
          <div className="bge-grid marquee">{renderCards(marquee)}</div>
        </section>
      )}
      <section className="bge-section">
        <header><span>Full Bowl Schedule</span><small>{standard.length} matchups</small></header>
        <div className="bge-grid">{renderCards(standard)}</div>
      </section>
    </section>
  );
}
