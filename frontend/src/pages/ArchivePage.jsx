import { useModule } from '../hooks/useModule.js';
import {
  PageHeader, SectionTitle, SourcePill, Skeleton, EmptyState,
  RetroCard, MilestoneRow, DecadeCard, CoachingTreeCard, LegacyCard, ThreadList,
} from '../components/index.js';

export default function ArchivePage() {
  const { data, loading, error } = useModule('archive');

  return (
    <>
      <PageHeader
        title="Dynasty Archive"
        sub="The record that grows with every season"
        actions={<SourcePill source={data?.source} />}
      />
      {loading ? <Skeleton height={400} />
        : error ? <EmptyState>Could not load the archive: {error}</EmptyState>
        : (
          <div className="grid-2" style={{ alignItems: 'start' }}>
            <div>
              <SectionTitle>Season Retrospectives</SectionTitle>
              {(data.season_retrospectives || []).length
                ? data.season_retrospectives.map((r, i) => <RetroCard key={i} retro={r} />)
                : <EmptyState />}
              <SectionTitle style={{ marginTop: 20 }}>Program Milestones</SectionTitle>
              {(data.milestones || []).length
                ? data.milestones.map((m, i) => <MilestoneRow key={i} milestone={m} />)
                : <EmptyState />}
              {data.decade_retrospective && <DecadeCard decade={data.decade_retrospective} />}
            </div>
            <div>
              <SectionTitle>Coaching Tree</SectionTitle>
              {data.coaching_tree && <CoachingTreeCard tree={data.coaching_tree} />}
              <SectionTitle style={{ marginTop: 20 }}>Player Legacies</SectionTitle>
              {(data.player_legacies || []).length
                ? data.player_legacies.map((p, i) => <LegacyCard key={i} player={p} />)
                : <EmptyState />}
              <SectionTitle style={{ marginTop: 20 }}>Narrative Threads</SectionTitle>
              <ThreadList threads={(data.narrative_threads || []).slice().reverse()} />
            </div>
          </div>
        )}
    </>
  );
}
