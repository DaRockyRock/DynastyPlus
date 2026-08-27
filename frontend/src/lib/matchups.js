// Marquee matchup selection. Ranks the week's national slate (the save's
// national.scoreboard) by game quality so the home page can surface the
// biggest games of the week. Pure and deterministic: the same scoreboard
// always produces the same board.
//
// The quality score is driven by the AP rankings on each side:
//   - each ranked team contributes (26 - rank) points, so #1 is worth 25
//     and #25 is worth 1; unranked teams contribute 0
//   - ranked vs ranked adds a +10 stakes bonus, top-10 vs top-10 adds +15
//     more, and top-5 vs top-5 another +10 (the blockbusters separate)
//   - evenly matched ranked pairs earn up to +8 as the rank gap closes
//   - conference games add +4 (standings and tiebreaker stakes)

const MAX_SCORE = 25 + 24 + 10 + 15 + 10 + 8 + 4; // a #1 vs #2 conference game

function rankPoints(rank) {
  return rank ? 26 - rank : 0;
}

export function matchupScore(game) {
  const hr = game.home?.rank ?? null;
  const ar = game.away?.rank ?? null;
  let score = rankPoints(hr) + rankPoints(ar);
  if (hr && ar) {
    score += 10;
    if (hr <= 10 && ar <= 10) score += 15;
    if (hr <= 5 && ar <= 5) score += 10;
    score += Math.max(0, 8 - Math.abs(hr - ar) / 2);
  }
  if (game.conference_game) score += 4;
  return score;
}

// 0-100 normalization of the raw score, for the on-card quality readout.
export function matchupQuality(game) {
  return Math.max(1, Math.min(100, Math.round((matchupScore(game) / MAX_SCORE) * 100)));
}

// Broadcast-style label for the card kicker.
export function matchupTag(game) {
  const hr = game.home?.rank ?? null;
  const ar = game.away?.rank ?? null;
  if (hr && ar) {
    if (hr <= 5 && ar <= 5) return 'Top-5 Showdown';
    if (hr <= 10 && ar <= 10) return 'Top-10 Showdown';
    return 'Ranked Matchup';
  }
  if ((hr && hr <= 10) || (ar && ar <= 10)) return 'Upset Watch';
  if (game.conference_game) return 'Conference Stakes';
  return 'National Slate';
}

// The board: scoreboard entries decorated with {score, quality, tag}, sorted
// best first. Ties break toward the better-ranked team, then alphabetically,
// so re-renders never reshuffle the rail.
export function rankMatchups(scoreboard, { limit = 4 } = {}) {
  const games = (Array.isArray(scoreboard) ? scoreboard : []).map((g) => ({
    ...g,
    score: matchupScore(g),
    quality: matchupQuality(g),
    tag: matchupTag(g),
  }));
  games.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    const aBest = Math.min(a.home?.rank ?? 99, a.away?.rank ?? 99);
    const bBest = Math.min(b.home?.rank ?? 99, b.away?.rank ?? 99);
    if (aBest !== bBest) return aBest - bBest;
    return String(a.home?.name).localeCompare(String(b.home?.name));
  });
  return games.slice(0, limit);
}
