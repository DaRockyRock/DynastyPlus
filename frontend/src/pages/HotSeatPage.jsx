import { useModule } from '../hooks/useModule.js';
import {
  PageHeader, SectionTitle, SourcePill, RegenerateButton, Skeleton, EmptyState, Card,
  HeatRow, ArticleFull, CandidateCard, SearchBlock,
} from '../components/index.js';

export default function HotSeatPage() {
  const { data, loading, error, regenerate, regenerating } = useModule('hot_seat');

  return (
    <>
      <PageHeader
        title="Coaching Hot Seat"
        sub="Heat index, the carousel, and the candidate board"
        actions={<>
          <SourcePill source={data?.source} />
          <RegenerateButton onClick={regenerate} spinning={regenerating} />
        </>}
      />
      {loading ? <Skeleton height={400} />
        : error ? <EmptyState>Could not load the hot seat: {error}</EmptyState>
        : (
          <>
            <div className="grid-2" style={{ alignItems: 'start' }}>
              <div>
                <SectionTitle>Heat Index</SectionTitle>
                <Card style={{ padding: '8px 12px' }}>
                  {(data.coaches || []).map((c, i) => <HeatRow key={i} coach={c} />)}
                </Card>
              </div>
              <div>
                <SectionTitle>Carousel Coverage</SectionTitle>
                {(data.articles || []).map((a, i) => (
                  <ArticleFull key={i} article={{ ...a, reporter: a.reporter || '', dek: a.dek || '', timestamp: a.timestamp || '' }} />
                ))}
                <SectionTitle style={{ marginTop: 20 }}>Candidate Board</SectionTitle>
                {(data.candidate_pool || []).map((c, i) => <CandidateCard key={i} candidate={c} />)}
              </div>
            </div>
            {data.active_search && <SearchBlock search={data.active_search} />}
          </>
        )}
    </>
  );
}
