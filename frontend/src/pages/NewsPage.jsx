import { useModule } from '../hooks/useModule.js';
import { useApp } from '../context/AppContext.jsx';
import {
  PageHeader, SectionTitle, SourcePill, RegenerateButton, Skeleton, EmptyState,
  ArticleFull, InsiderReportCard, OutletList,
} from '../components/index.js';

export default function NewsPage() {
  const { openArticle } = useApp();
  const { data, loading, error, regenerate, regenerating } = useModule('news_feed');

  return (
    <>
      <PageHeader
        title="News Feed"
        sub="National and program coverage from across the dynasty media universe"
        actions={<>
          <SourcePill source={data?.source} />
          <RegenerateButton onClick={regenerate} spinning={regenerating} />
        </>}
      />
      {loading ? <Skeleton height={400} />
        : error ? <EmptyState>Could not load the feed: {error}</EmptyState>
        : (
          <div className="grid-2" style={{ alignItems: 'start' }}>
            <div>
              <SectionTitle>National</SectionTitle>
              {(data.national || []).length
                ? data.national.map((a, i) => <ArticleFull key={i} article={a} onClick={() => openArticle(a)} />)
                : <EmptyState>No items.</EmptyState>}
              <SectionTitle style={{ marginTop: 26 }}>Coaching Carousel - Insider Reports</SectionTitle>
              {(data.insider_reports || []).length
                ? data.insider_reports.map((r, i) => <InsiderReportCard key={i} report={r} />)
                : <EmptyState>No items.</EmptyState>}
            </div>
            <div>
              <SectionTitle>Program</SectionTitle>
              {(data.program || []).length
                ? data.program.map((a, i) => <ArticleFull key={i} article={a} onClick={() => openArticle(a)} />)
                : <EmptyState>No items.</EmptyState>}
              <SectionTitle style={{ marginTop: 26 }}>Outlets &amp; Reliability</SectionTitle>
              <OutletList outlets={data.outlets || []} />
            </div>
          </div>
        )}
    </>
  );
}
