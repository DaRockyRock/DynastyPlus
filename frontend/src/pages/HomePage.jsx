import { useState } from 'react';
import { useApp } from '../context/AppContext.jsx';
import { useModule } from '../hooks/useModule.js';
import {
  SectionTitle, SourcePill, RegenerateButton, Skeleton, EmptyState, Card,
  StorySlider, ArticleCard, StatCard, RankingList, ResultCard, NextGameCard, RankingsModal,
  MarqueeMatchups,
} from '../components/index.js';

export default function HomePage() {
  const { dynasty, openArticle, setActiveTab } = useApp();
  const [rankingsOpen, setRankingsOpen] = useState(false);
  const stories = useModule('top_stories');
  const news = useModule('news_feed');
  if (!dynasty) return null;

  const t = dynasty.team;
  const r = t.stats.ranks || {};
  const cfp = (dynasty.national.cfp_top12 || []).slice(0, 8);
  const last = (dynasty.schedule.recent_results || [])[0];
  const up = dynasty.schedule.upcoming;
  const scoreboard = dynasty.national.scoreboard || [];

  return (
    <div className="home-grid">
      <div className="home-main">
        {/* Top stories */}
        <SectionTitle right={<>
          <SourcePill source={stories.data?.source} />
          <RegenerateButton onClick={stories.regenerate} spinning={stories.regenerating} />
        </>}>
          Top Stories
        </SectionTitle>
        {stories.loading ? <Skeleton height={420} />
          : stories.error ? <EmptyState>Could not load stories: {stories.error}</EmptyState>
          : <StorySlider stories={stories.data?.stories || []} watermarkEspnId={t.espn_id} onOpen={openArticle} />}

        {/* Marquee matchups: the week's biggest games, ranked off the polls */}
        {scoreboard.length > 0 && (
          <div className="home-sub">
            <SectionTitle note="Ranked by the matchup algorithm">Marquee Matchups</SectionTitle>
            <MarqueeMatchups scoreboard={scoreboard} />
          </div>
        )}

        {/* News columns */}
        <div className="news-columns">
          <div>
            <SectionTitle right={<SourcePill source={news.data?.source} />}>National</SectionTitle>
            {news.loading ? <Skeleton height={220} />
              : (news.data?.national || []).length
                ? news.data.national.slice(0, 4).map((a, i) => <ArticleCard key={i} article={a} onClick={() => openArticle(a)} />)
                : <EmptyState>No articles.</EmptyState>}
          </div>
          <div>
            <SectionTitle>Program</SectionTitle>
            {news.loading ? <Skeleton height={220} />
              : (news.data?.program || []).length
                ? news.data.program.slice(0, 4).map((a, i) => <ArticleCard key={i} article={a} onClick={() => openArticle(a)} />)
                : <EmptyState>No articles.</EmptyState>}
          </div>
        </div>
      </div>

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="stat-cards">
          <StatCard label="Scoring Offense" value={t.stats.points_per_game} unit="ppg"
            nationalRank={r.points_per_game?.national} confRank={r.points_per_game?.conference} conference={t.conference} />
          <StatCard label="Scoring Defense" value={t.stats.points_allowed} unit="ppg"
            nationalRank={r.points_allowed?.national} confRank={r.points_allowed?.conference} conference={t.conference} />
          <StatCard label="Total Offense" value={t.stats.yards_per_game} unit="ypg"
            nationalRank={r.yards_per_game?.national} confRank={r.yards_per_game?.conference} conference={t.conference} />
          <StatCard label="Turnover Margin" value={`${t.stats.turnover_margin > 0 ? '+' : ''}${t.stats.turnover_margin}`}
            nationalRank={r.turnover_margin?.national} confRank={r.turnover_margin?.conference} conference={t.conference} />
        </div>

        {last && <ResultCard result={last} onClick={dynasty.last_game ? () => setActiveTab('gamecenter') : undefined} />}
        {up && <NextGameCard game={up} />}

        <Card className="panel rankings-link" onClick={() => setRankingsOpen(true)}>
          <div className="panel-head"><h3>CFP Top 8</h3><span className="panel-cta">Full rankings &rarr;</span></div>
          <RankingList teams={cfp} userTeam={t.name} />
        </Card>
      </aside>

      <RankingsModal
        open={rankingsOpen}
        national={dynasty.national}
        userTeam={t.name}
        initialPoll="cfp"
        onClose={() => setRankingsOpen(false)}
      />
    </div>
  );
}
