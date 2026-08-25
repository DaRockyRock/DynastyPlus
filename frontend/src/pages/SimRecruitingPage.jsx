import { useState, useEffect, useMemo } from 'react';
import { useTools } from '../context/ToolsContext.jsx';
import { api } from '../lib/api.js';
import {
  PageHeader, Skeleton, EmptyState, RecruitFilters, RecruitBoard,
} from '../components/index.js';

const NUMERIC_DESC = new Set(['ovr', 'stars', 'expected_nil', 'status']);

// Browse the full national class as it commits week to week. Offers to the
// user's board recruits happen on the NIL tab.
export default function SimRecruitingPage() {
  const { simActive, pointer, reloadKey } = useTools();
  const [national, setNational] = useState(null);
  const [filters, setFilters] = useState({ q: '', position: '', stars: '0', status: 'all' });
  const [sort, setSort] = useState({ key: 'national_rank', dir: 1 });

  useEffect(() => {
    if (!simActive) return undefined;
    let cancelled = false;
    api.simRecruits(pointer.year)
      .then((d) => { if (!cancelled) setNational(d.recruits || []); })
      .catch(() => { if (!cancelled) setNational([]); });
    return () => { cancelled = true; };
  }, [simActive, pointer.year, pointer.week, reloadKey]);

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

  if (!simActive) return <EmptyState>Start a season to populate the national recruiting board.</EmptyState>;

  return (
    <>
      <PageHeader title="National Recruiting Board" sub="The full FBS class, week to week" />
      {national == null ? <Skeleton height={400} /> : (
        <>
          <RecruitFilters value={filters} onChange={setFilters} count={filtered.length} />
          <RecruitBoard recruits={filtered} sort={sort} onSort={onSort} />
        </>
      )}
    </>
  );
}
