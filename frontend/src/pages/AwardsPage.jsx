import { useModule } from '../hooks/useModule.js';
import {
  PageHeader, SectionTitle, SourcePill, RegenerateButton, Skeleton, EmptyState,
  AwardBlock, VoterCard,
} from '../components/index.js';

export default function AwardsPage() {
  const { data, loading, error, regenerate, regenerating } = useModule('awards');

  const notesFor = (key) => (data?.panel_notes || []).filter((n) => n.award === key);

  return (
    <>
      <PageHeader
        title="Awards Watch"
        sub="Heisman and the position races, tracked by a voter panel"
        actions={<>
          <SourcePill source={data?.source} />
          <RegenerateButton onClick={regenerate} spinning={regenerating} />
        </>}
      />
      {loading ? <Skeleton height={400} />
        : error ? <EmptyState>Could not load awards: {error}</EmptyState>
        : (
          <>
            <div className="grid-2" style={{ alignItems: 'start' }}>
              {(data.awards || []).map((a) => (
                <AwardBlock
                  key={a.key}
                  award={{
                    name: a.name,
                    criteria: a.criteria,
                    candidates: (data.watch || {})[a.key] || [],
                    notes: notesFor(a.key),
                  }}
                />
              ))}
            </div>
            <SectionTitle style={{ marginTop: 24 }}>Voter Panel</SectionTitle>
            <div className="grid-3">
              {(data.voter_panel || []).map((v, i) => <VoterCard key={i} voter={v} />)}
            </div>
          </>
        )}
    </>
  );
}
