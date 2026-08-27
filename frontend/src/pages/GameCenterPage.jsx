import { useState } from 'react';
import { useApp } from '../context/AppContext.jsx';
import {
  SectionTitle, Card, EmptyState, SegmentedControl,
  GameScoreHeader, TeamStatComparison, ScoringSummary, DriveChart, KeyPlaysList, BoxScoreTable,
} from '../components/index.js';

// The Game Center: the full box score, scoring summary, drive chart, and key
// plays for the user's most recent game (dynasty.last_game). The reporters in the
// post-game presser see this whole game; here the coach can review it.
export default function GameCenterPage() {
  const { dynasty } = useApp();
  const game = dynasty?.last_game;
  const [side, setSide] = useState(null);
  if (!dynasty) return null;
  if (!game) {
    return <EmptyState>No game yet. The Game Center opens once your team has played.</EmptyState>;
  }
  const userSide = game.user_is_home ? 'home' : 'away';
  const active = side || userSide;
  const sideOptions = [
    { value: 'away', label: game.away.abbr },
    { value: 'home', label: game.home.abbr },
  ];

  return (
    <div className="gc">
      <GameScoreHeader game={game} coaches={dynasty.coaches} />

      <div className="gc-grid">
        <div className="gc-col">
          <SectionTitle>Team Stats</SectionTitle>
          <Card className="gc-panel"><TeamStatComparison game={game} /></Card>

          <SectionTitle>Scoring Summary</SectionTitle>
          <Card className="gc-panel"><ScoringSummary scoring={game.scoring_summary} /></Card>
        </div>

        <div className="gc-col">
          <SectionTitle>Key Plays</SectionTitle>
          <Card className="gc-panel"><KeyPlaysList plays={game.key_plays} /></Card>

          <SectionTitle>Drives</SectionTitle>
          <Card className="gc-panel gc-panel-scroll"><DriveChart drives={game.drives} /></Card>
        </div>
      </div>

      <SectionTitle right={<SegmentedControl options={sideOptions} value={active} onChange={setSide} />}>
        Box Score
      </SectionTitle>
      <Card className="gc-panel">
        <BoxScoreTable box={game.box?.[active]} isUser={active === userSide} />
      </Card>
    </div>
  );
}
