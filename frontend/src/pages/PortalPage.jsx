import { useModule } from '../hooks/useModule.js';
import { noEmDash } from '../lib/format.js';
import {
  PageHeader, SectionTitle, SourcePill, RegenerateButton, Skeleton, EmptyState, Card,
  RumorCard, ClassGradeCard, MoveRow, NilCallout,
} from '../components/index.js';

export default function PortalPage() {
  const { data, loading, error, regenerate, regenerating } = useModule('portal');

  return (
    <>
      <PageHeader
        title="Transfer Portal"
        sub="Rumors, movement, and class grades"
        actions={<>
          <SourcePill source={data?.source} />
          <RegenerateButton onClick={regenerate} spinning={regenerating} />
        </>}
      />
      {loading ? <Skeleton height={400} />
        : error ? <EmptyState>Could not load the portal: {error}</EmptyState>
        : (
          <div className="grid-2" style={{ alignItems: 'start' }}>
            <div>
              <SectionTitle>Portal Rumors</SectionTitle>
              {(data.rumors || []).length
                ? data.rumors.map((r, i) => <RumorCard key={i} rumor={r} />)
                : <EmptyState>Quiet for now.</EmptyState>}
            </div>
            <div>
              {data.class_grade && <ClassGradeCard grade={data.class_grade} />}
              <SectionTitle>Incoming</SectionTitle>
              <Card className="panel">
                {(data.incoming || []).length
                  ? data.incoming.map((p, i) => <MoveRow key={i} player={p} kind="in" />)
                  : <div className="muted" style={{ padding: 8 }}>None.</div>}
              </Card>
              <SectionTitle style={{ marginTop: 18 }}>Outgoing</SectionTitle>
              <Card className="panel">
                {(data.outgoing || []).length
                  ? data.outgoing.map((p, i) => <MoveRow key={i} player={p} kind="out" />)
                  : <div className="muted" style={{ padding: 8 }}>None.</div>}
              </Card>
              <SectionTitle style={{ marginTop: 18 }}>Targets</SectionTitle>
              <Card className="panel">
                {(data.targets || []).length
                  ? data.targets.map((p, i) => <MoveRow key={i} player={p} kind="target" />)
                  : <div className="muted" style={{ padding: 8 }}>None.</div>}
              </Card>
              <SectionTitle style={{ marginTop: 18 }}>NIL Narrative</SectionTitle>
              <NilCallout>{noEmDash(data.nil_narrative || '')}</NilCallout>
            </div>
          </div>
        )}
    </>
  );
}
