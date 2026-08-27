import { useState, useEffect, useMemo } from 'react';
import { useModule } from '../hooks/useModule.js';
import { useBudget } from '../hooks/useBudget.js';
import { useApp } from '../context/AppContext.jsx';
import { api } from '../lib/api.js';
import { noEmDash } from '../lib/format.js';
import {
  PageHeader, SectionTitle, SourcePill, RegenerateButton, Skeleton, EmptyState, Card,
  StatCard, NilCallout, ProspectCard, CrystalBallCard, VisitCard,
  SegmentedControl, RecruitFilters, RecruitBoard,
} from '../components/index.js';

const NUMERIC_DESC = new Set(['ovr', 'stars', 'expected_nil', 'status']);

export default function RecruitingPage() {
  const { data, loading, error, regenerate, regenerating } = useModule('recruiting');
  const { snapshot } = useBudget();
  const { simActive, pointer, reloadKey, textPerson } = useApp();
  const budgetByName = Object.fromEntries((snapshot?.recruiting_nil || []).map((r) => [r.name, r]));

  const [view, setView] = useState('mine');
  const [national, setNational] = useState(null);
  const [filters, setFilters] = useState({ q: '', position: '', stars: '0', status: 'all' });
  const [sort, setSort] = useState({ key: 'national_rank', dir: 1 });

  // Fetch the national class when viewing it (and refresh as the season advances).
  useEffect(() => {
    if (!simActive || view !== 'national') return undefined;
    let cancelled = false;
    api.simRecruits(pointer.year)
      .then((d) => { if (!cancelled) setNational(d.recruits || []); })
      .catch(() => { if (!cancelled) setNational([]); });
    return () => { cancelled = true; };
  }, [simActive, view, pointer.year, pointer.week, reloadKey]);

  const onSort = (key) =>
    setSort((s) => (s.key === key ? { key, dir: -s.dir } : { key, dir: NUMERIC_DESC.has(key) ? -1 : 1 }));

  const filtered = useMemo(() => {
    let list = national || [];
    const f = filters;
    if (f.q) {
      const q = f.q.toLowerCase();
      list = list.filter((r) => r.name.toLowerCase().includes(q) || (r.state || '').toLowerCase().includes(q));
    }
    if (f.position) list = list.filter((r) => r.position === f.position);
    if (f.stars && f.stars !== '0') list = list.filter((r) => r.stars >= Number(f.stars));
    if (f.status === 'open') list = list.filter((r) => !r.committed_to);
    else if (f.status === 'committed') list = list.filter((r) => r.committed_to);
    else if (f.status === 'signed') list = list.filter((r) => r.status === 'Signed');
    const val = (r) => (sort.key === 'status' ? (r.committed_to ? 1 : 0) : sort.key === 'name' ? r.name : r[sort.key]);
    return [...list].sort((a, b) => {
      const av = val(a); const bv = val(b);
      if (av < bv) return -sort.dir;
      if (av > bv) return sort.dir;
      return 0;
    });
  }, [national, filters, sort]);

  return (
    <>
      <PageHeader
        title="Recruiting Board"
        sub="Rankings, scouting, crystal balls, and NIL"
        actions={<>
          <SourcePill source={data?.source} />
          <RegenerateButton onClick={regenerate} spinning={regenerating} />
        </>}
      />

      {simActive && (
        <div className="recruit-views">
          <SegmentedControl
            options={[{ value: 'mine', label: 'My Board' }, { value: 'national', label: 'National Board' }]}
            value={view}
            onChange={setView}
          />
        </div>
      )}

      {simActive && view === 'national' ? (
        national == null ? <Skeleton height={400} /> : (
          <>
            <RecruitFilters value={filters} onChange={setFilters} count={filtered.length} />
            <RecruitBoard
              recruits={filtered}
              sort={sort}
              onSort={onSort}
              onSelect={(r) => textPerson({ name: r.name, kind: 'recruit' })}
            />
          </>
        )
      ) : loading ? <Skeleton height={400} />
        : error ? <EmptyState>Could not load the board: {error}</EmptyState>
        : (
          <>
            <Card style={{ padding: 18, marginBottom: 22, display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap' }}>
              <StatCard label="National Class Rank" value={`#${data.class_rank_national ?? '-'}`} />
              <StatCard label="Conference Rank" value={`#${data.class_rank_conference ?? '-'}`} />
              <div style={{ flex: 1, minWidth: 240, color: 'var(--text-2)', fontSize: 13.5, lineHeight: 1.6 }}>
                {noEmDash(data.class_summary || '')}
              </div>
            </Card>

            <div className="grid-2" style={{ alignItems: 'start' }}>
              <div>
                <SectionTitle>Commitments</SectionTitle>
                {(data.commits || []).length
                  ? data.commits.map((c, i) => <ProspectCard key={i} prospect={c} budget={budgetByName[c.name]} committed />)
                  : <EmptyState />}
              </div>
              <div>
                <SectionTitle>Top Targets</SectionTitle>
                {(data.targets || []).length
                  ? data.targets.map((c, i) => <ProspectCard key={i} prospect={c} budget={budgetByName[c.name]} />)
                  : <EmptyState />}
              </div>
            </div>

            <div className="grid-2" style={{ alignItems: 'start', marginTop: 24 }}>
              <div>
                <SectionTitle>Crystal Ball Predictions</SectionTitle>
                {(data.crystal_balls || []).length
                  ? data.crystal_balls.map((c, i) => <CrystalBallCard key={i} pick={c} />)
                  : <EmptyState />}
              </div>
              <div>
                <SectionTitle>Visit Recaps</SectionTitle>
                {(data.visit_recaps || []).length
                  ? data.visit_recaps.map((v, i) => <VisitCard key={i} visit={v} />)
                  : <EmptyState />}
                <SectionTitle style={{ marginTop: 20 }}>NIL Narrative</SectionTitle>
                <NilCallout>{noEmDash(data.nil_narrative || '')}</NilCallout>
              </div>
            </div>
          </>
        )}
    </>
  );
}
