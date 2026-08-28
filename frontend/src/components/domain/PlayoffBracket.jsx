import { useMemo } from 'react';
import BracketGame from './BracketGame.jsx';
import TeamLogo from '../ui/TeamLogo.jsx';
import { hexColor } from '../../lib/format.js';

// The playoff bracket, rendered from the backend bracket JSON
// (backend/playoff.build_bracket): one column per round plus the champion
// block, real game marks on every slot, bowl tie-ins and sites on every game,
// and SVG elbow connectors between feeders and their next game. Handles any
// format the engine can build: multi-tier byes (teams simply appear in the
// round they enter), a 2-team BCS-style title game, and the 1-team poll-era
// case (champion card only). Unplayed games never advance anyone: winner slots
// stay as "Winner, Rose Bowl" labels until results exist.

const COL_W = 224;
const COL_GAP = 38;
const GAME_H = 97;   // the two stacked 46px tiles + gap; the site label rides in GAME_GAP
const GAME_GAP = 34;
const HEAD_H = 34;
const SLOT_Y = [23, 74]; // connector anchor offsets: the tile centers
const CHAMP_BLOCK_H = 250;
const TROPHY_SRC = '/game-assets/bowls/championships/nationalchampionshiptrophy.png';

function championBlock(champion, label) {
  return (
    <>
      <img className="pb-trophy" src={TROPHY_SRC} alt="CFP National Championship trophy"
           onError={(e) => { e.currentTarget.style.display = 'none'; }} />
      {champion ? (
        <div className="pb-champ-slot filled" style={{ '--tile': hexColor(champion.color, '#232a2e') }}
             title={champion.team}>
          <TeamLogo espnId={champion.espn_id} abbr={champion.abbr} name={champion.team} size={38} plate={false} />
        </div>
      ) : (
        <div className="pb-champ-slot" />
      )}
      <div className="pb-champ-title">{label}</div>
    </>
  );
}

export default function PlayoffBracket({ bracket, userTeamId, championLabel = 'National Champion' }) {
  const layout = useMemo(() => {
    if (!bracket || !bracket.rounds?.length) return null;
    const pos = {};
    const colBottom = [];

    // feederId -> the game that feeder's winner advances to, so a feeder can be
    // aligned behind the matchup it feeds into. A slot keeps its feeder game id
    // (`game`) even after the winner is filled in as a team, so filled games
    // stay aligned on (and connected to) their feeders.
    const feedsInto = {};
    bracket.rounds.forEach((rnd) => {
      rnd.games.forEach((g) => {
        g.slots.forEach((s) => {
          if (s.game) feedsInto[s.game] = g.id;
        });
      });
    });

    const place = (g, c, desiredY) => {
      const minY = colBottom[c] ?? HEAD_H;
      pos[g.id] = { x: c * (COL_W + COL_GAP), y: Math.max(desiredY, minY) };
      colBottom[c] = pos[g.id].y + GAME_H + GAME_GAP;
    };
    const avgY = (ps) => ps.reduce((sum, p) => sum + p.y, 0) / ps.length;

    // Byes make a later round (not the first) the widest one, so anchor the
    // layout on the widest round. From the anchor rightward, center each game on
    // the feeders to its LEFT (the classic bracket layout). Rounds LEFT of the
    // anchor (a first round thinned by byes) instead align each game behind the
    // matchup its winner feeds into, to its RIGHT, so a feeder sits directly
    // behind its next game rather than being stacked out of line. With no byes
    // the first round is already the widest, so the anchor is round 0 and this
    // reduces to the classic left-to-right pass.
    let anchor = 0;
    bracket.rounds.forEach((rnd, c) => {
      if (rnd.games.length > bracket.rounds[anchor].games.length) anchor = c;
    });

    for (let c = anchor; c < bracket.rounds.length; c += 1) {
      bracket.rounds[c].games.forEach((g) => {
        const feeders = g.slots
          .filter((s) => s.game && pos[s.game])
          .map((s) => pos[s.game]);
        place(g, c, feeders.length ? avgY(feeders) : (colBottom[c] ?? HEAD_H));
      });
    }
    for (let c = anchor - 1; c >= 0; c -= 1) {
      // Place in the order of the matchups they feed, so vertical order and the
      // no-overlap stacking agree even if the round's game list is ordered
      // differently from its receiving column.
      const targetY = (g) => (feedsInto[g.id] && pos[feedsInto[g.id]] ? pos[feedsInto[g.id]].y : Infinity);
      [...bracket.rounds[c].games]
        .sort((a, b) => targetY(a) - targetY(b))
        .forEach((g) => {
          const ty = targetY(g);
          place(g, c, Number.isFinite(ty) ? ty : (colBottom[c] ?? HEAD_H));
        });
    }

    const lastRound = bracket.rounds[bracket.rounds.length - 1];
    const finalGame = lastRound.games[0];
    const finalPos = pos[finalGame.id];
    const champ = { x: finalPos.x, y: finalPos.y + GAME_H + 22 };

    const width = bracket.rounds.length * (COL_W + COL_GAP) - COL_GAP;
    const height = Math.max(...colBottom, champ.y + CHAMP_BLOCK_H);

    const connectors = [];
    bracket.rounds.forEach((rnd) => {
      rnd.games.forEach((g) => {
        g.slots.forEach((s, i) => {
          if (!s.game || !pos[s.game]) return;
          const from = pos[s.game];
          const to = pos[g.id];
          const x1 = from.x + COL_W;
          const y1 = from.y + GAME_H / 2;
          const x2 = to.x;
          const y2 = to.y + SLOT_Y[i];
          const mid = x1 + COL_GAP / 2;
          connectors.push(`M ${x1} ${y1} H ${mid} V ${y2} H ${x2}`);
        });
      });
    });

    return { pos, width, height, champ, finalId: finalGame.id, connectors };
  }, [bracket]);

  if (!bracket) return null;

  // A one-team field: no games, the top-ranked team is crowned outright.
  if (!bracket.rounds?.length) {
    return (
      <div className="pb-scroll">
        <div className="pb-champ-solo">
          {championBlock(bracket.champion, championLabel)}
          {bracket.champion_note && <p className="pb-note">{bracket.champion_note}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="pb-scroll">
      <div className="pb-canvas" style={{ width: layout.width, height: layout.height }}>
        <svg className="pb-connectors" width={layout.width} height={layout.height}>
          {layout.connectors.map((d, i) => <path key={i} d={d} />)}
        </svg>
        {bracket.rounds.map((rnd, c) => (
          <div key={rnd.round} className="pb-colhead" style={{ left: c * (COL_W + COL_GAP), width: COL_W }}>
            {rnd.name}
          </div>
        ))}
        {bracket.rounds.map((rnd) => rnd.games.map((g) => (
          <div key={g.id} style={{ position: 'absolute', left: layout.pos[g.id].x, top: layout.pos[g.id].y, width: COL_W }}>
            <BracketGame game={g} userTeamId={userTeamId} final={g.id === layout.finalId} />
          </div>
        )))}
        <div className="pb-champ-block" style={{ left: layout.champ.x, top: layout.champ.y, width: COL_W }}>
          {championBlock(bracket.champion, championLabel)}
        </div>
      </div>
    </div>
  );
}
