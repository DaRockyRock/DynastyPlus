// Storybook fixtures for the Dynasty+ Tools editors.

export const ranking = [
  { rank: 1, team: 'Georgia Bulldogs', abbr: 'UGA', espn_id: 61, record: '9-0' },
  { rank: 2, team: 'Texas Longhorns', abbr: 'TEX', espn_id: 251, record: '9-0' },
  { rank: 3, team: 'Ohio State Buckeyes', abbr: 'OSU', espn_id: 194, record: '8-1' },
  { rank: 4, team: 'Oregon Ducks', abbr: 'ORE', espn_id: 2483, record: '9-0' },
  { rank: 5, team: 'Nebraska Cornhuskers', abbr: 'NEB', espn_id: 158, record: '8-1' },
];
export const committeeBallot = [
  { rank: 1, team: 'Georgia Bulldogs', abbr: 'UGA', espn_id: 61, record: '9-0' },
  { rank: 2, team: 'Texas Longhorns', abbr: 'TEX', espn_id: 251, record: '9-0' },
  { rank: 3, team: 'Ohio State Buckeyes', abbr: 'OSU', espn_id: 194, record: '8-1' },
  { rank: 4, team: 'Oregon Ducks', abbr: 'ORE', espn_id: 2483, record: '9-0' },
  { rank: 5, team: 'Nebraska Cornhuskers', abbr: 'NEB', espn_id: 158, record: '8-1' },
  { rank: 6, team: 'Alabama Crimson Tide', abbr: 'ALA', espn_id: 333, record: '8-1' },
  { rank: 7, team: 'Penn State Nittany Lions', abbr: 'PSU', espn_id: 213, record: '8-1' },
  { rank: 8, team: 'Notre Dame Fighting Irish', abbr: 'ND', espn_id: 87, record: '8-1' },
  { rank: 9, team: 'Tennessee Volunteers', abbr: 'TENN', espn_id: 2633, record: '7-2' },
  { rank: 10, team: 'Clemson Tigers', abbr: 'CLEM', espn_id: 228, record: '8-1' },
  { rank: 11, team: 'Miami Hurricanes', abbr: 'MIA', espn_id: 2390, record: '8-1' },
  { rank: 12, team: 'Indiana Hoosiers', abbr: 'IND', espn_id: 84, record: '7-2' },
];

// --- Custom playoff bracket (mirrors backend/playoff.build_bracket output) ---
// A tiny structural mirror of the backend engine so stories can preview any
// format without the API. Teams are weighted 2**byes and the seed list splits
// recursively into equal-weight halves (ties alternate sides), which is exactly
// how backend/playoff.py builds the real thing.
const NY6 = [
  { key: 'peach', name: 'Peach Bowl', venue: 'Mercedes-Benz Stadium', city: 'Atlanta, GA', asset: 'peachbowl' },
  { key: 'rose', name: 'Rose Bowl', venue: 'Rose Bowl', city: 'Pasadena, CA', asset: 'rosebowl' },
  { key: 'fiesta', name: 'Fiesta Bowl', venue: 'State Farm Stadium', city: 'Glendale, AZ', asset: 'fiestabowl' },
  { key: 'sugar', name: 'Sugar Bowl', venue: 'Caesars Superdome', city: 'New Orleans, LA', asset: 'sugarbowl' },
  { key: 'cotton', name: 'Cotton Bowl', venue: 'AT&T Stadium', city: 'Arlington, TX', asset: 'cottonbowl' },
  { key: 'orange', name: 'Orange Bowl', venue: 'Hard Rock Stadium', city: 'Miami Gardens, FL', asset: 'orangebowl' },
];

// Primary colors for the bracket tile art (mirrors what the backend pool
// carries from the team directory).
const TEAM_COLORS = {
  61: 'ba0c2f', 251: 'bf5700', 194: 'bb0000', 2483: '154733', 158: 'e41c38', 333: '9e1b32',
  213: '041e42', 87: '0c2340', 2633: 'ff8200', 228: 'f56600', 2390: 'f47321', 84: '990000',
  99: '461d7c', 57: '0021a5', 30: '990000', 130: '00274c', 2294: '000000', 52: '782f40',
  275: 'c5050c', 38: 'cfb87c', 356: 'e84a27', 120: 'e03a3e', 127: '18453b', 264: '4b2e83',
};

// Short school names for the fixture teams (mirrors backend/school_names.py).
const TEAM_SHORT_NAMES = {
  61: 'Georgia', 251: 'Texas', 194: 'Ohio State', 2483: 'Oregon', 158: 'Nebraska',
  333: 'Alabama', 213: 'Penn State', 87: 'Notre Dame', 2633: 'Tennessee', 228: 'Clemson',
  2390: 'Miami', 84: 'Indiana', 99: 'LSU', 57: 'Florida', 30: 'USC', 130: 'Michigan',
  2294: 'Iowa', 52: 'Florida State', 275: 'Wisconsin', 38: 'Colorado', 356: 'Illinois',
  120: 'Maryland', 127: 'Michigan State', 264: 'Washington',
};

// Campus cities for the fixture teams (mirrors backend/school_sites.py).
const TEAM_CITIES = {
  61: 'Athens, GA', 251: 'Austin, TX', 194: 'Columbus, OH', 2483: 'Eugene, OR',
  158: 'Lincoln, NE', 333: 'Tuscaloosa, AL', 213: 'State College, PA', 87: 'South Bend, IN',
  2633: 'Knoxville, TN', 228: 'Clemson, SC', 2390: 'Miami Gardens, FL', 84: 'Bloomington, IN',
  99: 'Baton Rouge, LA', 57: 'Gainesville, FL', 30: 'Los Angeles, CA', 130: 'Ann Arbor, MI',
  2294: 'Iowa City, IA', 52: 'Tallahassee, FL', 275: 'Madison, WI', 38: 'Boulder, CO',
  356: 'Champaign, IL', 120: 'College Park, MD', 127: 'East Lansing, MI', 264: 'Seattle, WA',
};

export const playoffTeams = [
  ...committeeBallot,
  { rank: 13, team: 'LSU Tigers', abbr: 'LSU', espn_id: 99, record: '7-2' },
  { rank: 14, team: 'Florida Gators', abbr: 'FLA', espn_id: 57, record: '7-2' },
  { rank: 15, team: 'USC Trojans', abbr: 'USC', espn_id: 30, record: '7-2' },
  { rank: 16, team: 'Michigan Wolverines', abbr: 'MICH', espn_id: 130, record: '7-2' },
  { rank: 17, team: 'Iowa Hawkeyes', abbr: 'IOWA', espn_id: 2294, record: '7-2' },
  { rank: 18, team: 'Florida State Seminoles', abbr: 'FSU', espn_id: 52, record: '6-3' },
  { rank: 19, team: 'Wisconsin Badgers', abbr: 'WIS', espn_id: 275, record: '6-3' },
  { rank: 20, team: 'Colorado Buffaloes', abbr: 'COLO', espn_id: 38, record: '6-3' },
  { rank: 21, team: 'Illinois Fighting Illini', abbr: 'ILL', espn_id: 356, record: '6-3' },
  { rank: 22, team: 'Maryland Terrapins', abbr: 'MD', espn_id: 120, record: '6-3' },
  { rank: 23, team: 'Michigan State Spartans', abbr: 'MSU', espn_id: 127, record: '6-3' },
  { rank: 24, team: 'Washington Huskies', abbr: 'WASH', espn_id: 264, record: '6-3' },
].map((t) => ({ ...t, color: TEAM_COLORS[t.espn_id], short: TEAM_SHORT_NAMES[t.espn_id] || t.team }));

function splitEntries(entries, size) {
  if (entries.length === 1) return entries[0];
  const half = size / 2;
  const a = []; const b = []; let wa = 0; let wb = 0; let toggle = true;
  entries.forEach((e) => {
    let pickA;
    if (wa === wb) { pickA = toggle; toggle = !toggle; } else { pickA = wa < wb; }
    if (pickA && wa + e.size > half) pickA = false;
    else if (!pickA && wb + e.size > half) pickA = true;
    if (pickA) { a.push(e); wa += e.size; } else { b.push(e); wb += e.size; }
  });
  return { a: splitEntries(a, half), b: splitEntries(b, half), size };
}

export function playoffBracketFixture(teams, byeTiers = []) {
  const n = teams.length;
  const seeds = teams.map((t, i) => ({ ...t, seed: i + 1, type: 'team' }));
  if (n === 1) {
    return {
      format: { teams: 1, byes: [] }, field_size: 1, customized: true, rounds: [],
      seeds, byes: [], selection: { auto_bids: [], first_out: [], excluded: [], notes: [], pool_size: 25 },
      champion: seeds[0],
      champion_note: 'With a one-team field the top-ranked team is crowned champion outright, as in the pre-BCS poll era.',
    };
  }
  const weights = [];
  [...byeTiers].sort((x, y) => y.rounds - x.rounds).forEach((t) => {
    for (let i = 0; i < t.teams; i += 1) weights.push(2 ** t.rounds);
  });
  while (weights.length < n) weights.push(1);
  const root = splitEntries(weights.map((w, i) => ({ seed: i + 1, size: w })), weights.reduce((s, w) => s + w, 0));
  const totalRounds = Math.log2(weights.reduce((s, w) => s + w, 0));

  const gamesByRound = new Map();
  const collect = (node) => {
    if (node.seed) return { type: 'seed', seed: node.seed };
    const r = Math.log2(node.size);
    const game = { round: r, slots: [collect(node.a), collect(node.b)] };
    if (!gamesByRound.has(r)) gamesByRound.set(r, []);
    gamesByRound.get(r).push(game);
    return { type: 'winner', game };
  };
  collect(root);

  const roundKeys = [...gamesByRound.keys()].sort((x, y) => x - y);
  roundKeys.forEach((r) => gamesByRound.get(r).forEach((g, i) => { g.id = `R${r}G${i + 1}`; }));

  const roundName = (r, count, ordinal) => {
    if (r === totalRounds) return 'National Championship';
    if (r === totalRounds - 1 && count === 2) return 'Semifinals';
    if (r === totalRounds - 2 && count === 4) return 'Quarterfinals';
    return `${['First', 'Second', 'Third', 'Fourth'][ordinal]} Round`;
  };

  let bowlIdx = 0; let ordinal = 0;
  const byes = [];
  const rounds = roundKeys.map((r, pos) => {
    const games = gamesByRound.get(r);
    const name = roundName(r, games.length, ordinal);
    if (name.endsWith('Round')) ordinal += 1;
    return {
      round: r,
      name,
      games: games.map((g) => {
        const slots = g.slots.map((s) => {
          if (s.type === 'seed') {
            const team = seeds[s.seed - 1];
            if (r > roundKeys[0]) byes.push({ ...team, first_round: r });
            return team;
          }
          return { type: 'winner', game: s.game.id, label: 'Winner' };
        });
        let site;
        if (r === totalRounds) {
          site = { type: 'championship', venue: 'Mercedes-Benz Stadium', city: 'Atlanta, GA', bowl: null };
        } else if (pos === 0 && slots[0].type === 'team') {
          site = { type: 'campus', venue: slots[0].team, city: TEAM_CITIES[slots[0].espn_id] || 'Campus site', bowl: null, host_espn_id: slots[0].espn_id };
        } else {
          const bowl = NY6[bowlIdx % NY6.length]; bowlIdx += 1;
          site = { type: 'bowl', venue: bowl.venue, city: bowl.city, bowl };
        }
        return { id: g.id, round: r, slots, site, status: 'scheduled', winner: null, scores: null };
      }),
    };
  });

  return {
    format: { teams: n, byes: byeTiers }, field_size: n, customized: false, total_rounds: totalRounds,
    rounds, seeds, byes,
    selection: { auto_bids: [], first_out: playoffTeams.slice(n, n + 2), excluded: [], notes: [], pool_size: 25 },
    champion: null,
  };
}

export const playoffBracket12 = playoffBracketFixture(playoffTeams.slice(0, 12), [{ teams: 4, rounds: 1 }]);
export const playoffBracket24 = playoffBracketFixture(playoffTeams, [{ teams: 8, rounds: 1 }]);
export const playoffBracket11DoubleBye = playoffBracketFixture(
  playoffTeams.slice(0, 11), [{ teams: 1, rounds: 2 }, { teams: 2, rounds: 1 }]);
export const playoffBracket2 = playoffBracketFixture(playoffTeams.slice(0, 2));
export const playoffBracket1 = playoffBracketFixture(playoffTeams.slice(0, 1));

// The 12-team bracket with the first round played: winners advance into the
// quarterfinal slots, losers dim, unplayed rounds stay open.
export const playoffBracket12Played = (() => {
  const b = JSON.parse(JSON.stringify(playoffBracket12));
  const r1 = b.rounds[0];
  const results = [[24, 20], [31, 13], [27, 24], [17, 34]];
  const winners = {};
  r1.games.forEach((g, i) => {
    const [hs, as] = results[i];
    g.scores = [hs, as];
    g.status = 'final';
    g.winner = (hs > as ? g.slots[0] : g.slots[1]).team;
    winners[g.id] = hs > as ? g.slots[0] : g.slots[1];
  });
  b.rounds[1].games.forEach((g) => {
    // a filled slot keeps its feeder game id, like the backend's advance does,
    // so the layout can align the game on its feeders and draw connectors
    g.slots = g.slots.map((s) => (s.type === 'winner' && winners[s.game]
      ? { ...winners[s.game], game: s.game } : s));
  });
  return b;
})();

// The playoff walkthrough guide payload (backend playoff_live._build_guide):
// mid-playoff, round 2 current with the user's game up next.
export const playoffGuide = {
  mode: 'cycle',
  status: 'in_progress',
  phases: [
    {
      key: 'selection', title: 'Reach the playoff', state: 'done',
      steps: [
        { id: 'season', label: 'Finish the season in CFB 27', state: 'done' },
        { id: 'arrive', label: 'Advance into bowl week, then exit', state: 'done' },
      ],
    },
    {
      key: 'round-1', title: 'First Round', state: 'done',
      progress: '64 of 64 recorded', user_line: 'You beat Bowling Green 42-10',
      steps: [
        { id: 'update', label: 'Update the dynasty file', state: 'done' },
        { id: 'load', label: 'Load your dynasty', state: 'done' },
        { id: 'play', label: 'Play your game vs Bowling Green Falcons', state: 'done' },
        { id: 'finish', label: 'Advance the week, then exit', state: 'done' },
      ],
    },
    {
      key: 'round-2', title: 'Second Round', state: 'current',
      progress: '19 of 32 recorded', user_line: 'Your game: vs Arkansas State Red Wolves',
      steps: [
        { id: 'update', label: 'Update the dynasty file', state: 'done',
          detail: "In CFB 27, exit the dynasty to the game's main menu, then press the Update Dynasty File button above." },
        { id: 'load', label: 'Load your dynasty', state: 'done',
          detail: 'Your matchup will be on the dynasty home screen.' },
        { id: 'play', label: 'Play your game vs Arkansas State Red Wolves', state: 'current',
          detail: 'It appears as Play Game on the Actions tab, like any other week.' },
        { id: 'finish', label: 'Advance the week, then exit', state: 'todo',
          detail: 'After your game, advance to the next week and exit to the main menu so your result and the simmed games are recorded.' },
        { id: 'repeat', label: 'Repeat until the round is recorded', state: 'todo',
          detail: 'A bowl week holds about 28 games, so this round takes several passes; the app rolls the week back and asks you to update again each time.' },
      ],
    },
    {
      key: 'round-3', title: 'Third Round', state: 'upcoming', progress: '0 of 16 recorded',
      steps: [
        { id: 'update', label: 'Update the dynasty file', state: 'todo' },
        { id: 'load', label: 'Load your dynasty', state: 'todo' },
      ],
    },
    {
      key: 'round-4', title: 'National Championship', state: 'upcoming', progress: '0 of 1 recorded',
      steps: [
        { id: 'update', label: 'Update the dynasty file', state: 'todo' },
        { id: 'load', label: 'Load your dynasty', state: 'todo' },
      ],
    },
  ],
};

// The same guide at the moment the playoff completes.
export const playoffGuideComplete = {
  mode: 'cycle',
  status: 'complete',
  phases: [
    ...playoffGuide.phases.map((p) => ({ ...p, state: 'done' })),
    {
      key: 'complete', title: 'Playoff complete', state: 'current',
      steps: [{
        id: 'done', label: 'Nebraska Cornhuskers win the championship', state: 'current',
        detail: 'Continue the dynasty as normal. Any leftover CFP games the game itself schedules in later bowl weeks are cosmetic and are not recorded.',
      }],
    },
  ],
};

const neb = { name: 'Nebraska Cornhuskers', abbr: 'NEB', espn_id: 158, rating: 77, is_user: true, rank: 14 };
const ore = { name: 'Oregon Ducks', abbr: 'ORE', espn_id: 2483, rating: 89, is_user: false, rank: 4 };
const osu = { name: 'Ohio State Buckeyes', abbr: 'OSU', espn_id: 194, rating: 92, is_user: false, rank: 1 };
const mich = { name: 'Michigan Wolverines', abbr: 'MICH', espn_id: 130, rating: 87, is_user: false, rank: 6 };
const iowa = { name: 'Iowa Hawkeyes', abbr: 'IOWA', espn_id: 2294, rating: 78, is_user: false, rank: null };

export const scoreboardGames = [
  { week: 5, home: neb, away: ore, conference: false, neutral: false, user: true,
    status: 'final', home_score: 31, away_score: 27, override: false, winner: 'Nebraska Cornhuskers' },
  { week: 5, home: osu, away: mich, conference: true, neutral: false, user: false,
    status: 'final', home_score: 24, away_score: 21, override: false, winner: 'Ohio State Buckeyes' },
  { week: 5, home: iowa, away: { name: 'Wisconsin Badgers', abbr: 'WIS', espn_id: 275, rating: 74, is_user: false, rank: null },
    conference: true, neutral: false, user: false,
    status: 'final', home_score: 17, away_score: 20, override: false, winner: 'Wisconsin Badgers' },
];

export const scoreboardUpcoming = [
  { week: 6, home: { name: 'USC Trojans', abbr: 'USC', espn_id: 30, rating: 80, is_user: false, rank: 12 },
    away: neb, conference: true, neutral: false, user: true,
    status: 'scheduled', home_score: null, away_score: null, override: false, winner: null },
];

// --- Conference Setup editor (mirrors GET /api/conferences/setup) ------------
// The FBS team directory the editor draws from. Full names + short school +
// abbr + real espn ids so TeamLogo renders the extracted game marks.
export const conferenceSetupTeams = [
  { name: 'Nebraska Cornhuskers', school: 'Nebraska', abbreviation: 'NEB', espn_id: 158, logo: '/game-assets/teams/158/logo.png' },
  { name: 'Ohio State Buckeyes', school: 'Ohio State', abbreviation: 'OSU', espn_id: 194, logo: '/game-assets/teams/194/logo.png' },
  { name: 'Iowa Hawkeyes', school: 'Iowa', abbreviation: 'IOWA', espn_id: 2294, logo: '/game-assets/teams/2294/logo.png' },
  { name: 'Wisconsin Badgers', school: 'Wisconsin', abbreviation: 'WIS', espn_id: 275, logo: '/game-assets/teams/275/logo.png' },
  { name: 'Michigan Wolverines', school: 'Michigan', abbreviation: 'MICH', espn_id: 130, logo: '/game-assets/teams/130/logo.png' },
  { name: 'Penn State Nittany Lions', school: 'Penn State', abbreviation: 'PSU', espn_id: 213, logo: '/game-assets/teams/213/logo.png' },
  { name: 'Clemson Tigers', school: 'Clemson', abbreviation: 'CLEM', espn_id: 228, logo: '/game-assets/teams/228/logo.png' },
  { name: 'Miami Hurricanes', school: 'Miami', abbreviation: 'MIA', espn_id: 2390, logo: '/game-assets/teams/2390/logo.png' },
  { name: 'Florida State Seminoles', school: 'Florida State', abbreviation: 'FSU', espn_id: 52, logo: '/game-assets/teams/52/logo.png' },
  { name: 'Notre Dame Fighting Irish', school: 'Notre Dame', abbreviation: 'ND', espn_id: 87, logo: '/game-assets/teams/87/logo.png' },
  { name: 'James Madison Dukes', school: 'James Madison', abbreviation: 'JMU', espn_id: 256, logo: '/game-assets/teams/256/logo.png' },
  { name: 'Marshall Thundering Herd', school: 'Marshall', abbreviation: 'MRSH', espn_id: 276, logo: '/game-assets/teams/276/logo.png' },
  { name: 'Old Dominion Monarchs', school: 'Old Dominion', abbreviation: 'ODU', espn_id: 295, logo: '/game-assets/teams/295/logo.png' },
  { name: 'Appalachian State Mountaineers', school: 'Appalachian State', abbreviation: 'APP', espn_id: 2026, logo: '/game-assets/teams/2026/logo.png' },
  { name: 'Southern Miss Golden Eagles', school: 'Southern Miss', abbreviation: 'USM', espn_id: 2572, logo: '/game-assets/teams/2572/logo.png' },
  { name: 'Troy Trojans', school: 'Troy', abbreviation: 'TROY', espn_id: 2653, logo: '/game-assets/teams/2653/logo.png' },
  { name: 'South Alabama Jaguars', school: 'South Alabama', abbreviation: 'USA', espn_id: 6, logo: '/game-assets/teams/6/logo.png' },
  { name: 'Coastal Carolina Chanticleers', school: 'Coastal Carolina', abbreviation: 'CCU', espn_id: 324, logo: '/game-assets/teams/324/logo.png' },
];

export const conferenceBigTen = {
  id: 'bigten', row: 1, key: 'BIG10', name: 'Big Ten', champ_game: 'Big Ten Championship',
  abbr: 'B1G', logo: '/game-assets/conferences/bigten.png', description: '', in_game: true,
  independents: false, divisions: [],
  teams: ['Nebraska Cornhuskers', 'Ohio State Buckeyes', 'Iowa Hawkeyes', 'Wisconsin Badgers', 'Michigan Wolverines', 'Penn State Nittany Lions'],
  rivalries: [
    { a: 'Nebraska Cornhuskers', b: 'Iowa Hawkeyes', name: 'Heroes Game' },
    { a: 'Ohio State Buckeyes', b: 'Michigan Wolverines', name: 'The Game' },
  ],
  limits: { min: 4, max: 20 },
};

export const conferenceAcc = {
  id: 'acc', row: 0, key: 'ACC', name: 'ACC', champ_game: 'ACC Championship',
  abbr: 'ACC', logo: '/game-assets/conferences/acc.png', description: '', in_game: true,
  independents: false, divisions: [],
  teams: ['Clemson Tigers', 'Miami Hurricanes', 'Florida State Seminoles'],
  rivalries: [],
  limits: { min: 4, max: 20 },
};

export const conferenceSunBelt = {
  id: 'sunbelt', row: 8, key: 'SBC', name: 'Sun Belt', champ_game: 'Sun Belt Championship',
  abbr: 'SBC', logo: '/game-assets/conferences/sunbelt.png',
  description: 'Fun Belt football: division play and December drama.', in_game: true,
  independents: false,
  divisions: [
    { row: 10, name: 'East', teams: ['James Madison Dukes', 'Marshall Thundering Herd', 'Old Dominion Monarchs', 'Appalachian State Mountaineers', 'Coastal Carolina Chanticleers'] },
    { row: 11, name: 'West', teams: ['Southern Miss Golden Eagles', 'Troy Trojans', 'South Alabama Jaguars'] },
  ],
  teams: [
    'James Madison Dukes', 'Marshall Thundering Herd', 'Old Dominion Monarchs', 'Appalachian State Mountaineers',
    'Coastal Carolina Chanticleers', 'Southern Miss Golden Eagles', 'Troy Trojans', 'South Alabama Jaguars',
  ],
  rivalries: [
    { a: 'Troy Trojans', b: 'South Alabama Jaguars', name: 'Battle for the Belt' },
  ],
  limits: { min: 4, max: 20 },
};

export const conferenceIndependents = {
  id: 'independents', row: 11, key: 'IND', name: 'FBS Independents', champ_game: '',
  abbr: 'IND', logo: '/game-assets/conferences/fbs.png', description: '', in_game: true,
  independents: true, divisions: [],
  teams: ['Notre Dame Fighting Irish'],
  rivalries: [],
  limits: null,
};

export const conferenceCustom = {
  id: 'custom-heartland', row: null, key: null, name: 'Heartland Alliance', champ_game: 'Heartland Title Game',
  abbr: 'HRT', logo: null,
  description: 'A companion-only super league built around the plains programs.', in_game: false,
  independents: false, divisions: [], teams: [], rivalries: [],
  limits: null,
};

export const applyGateLocked = {
  ok: false,
  reason: 'Conference changes can only be written to the game in the preseason or offseason.',
  phase: 'regular', week: 3,
};
export const applyGateReady = { ok: true, reason: '', phase: 'offseason', week: null };

export const applyResultSample = {
  written: 'C:\\Users\\ExampleUser\\Documents\\EA SPORTS College Football 27\\saves\\DYNASTY-CONFSETUP',
  report: [
    'Renamed Big Ten to Big Ten (no change needed)',
    'Moved Southern Miss Golden Eagles to Sun Belt West',
    'Renamed Sun Belt divisions to East and West',
  ],
  skipped: [
    'Heartland Alliance is a custom conference and stays in Dynasty+ only.',
  ],
};

export const conferenceSetupState = {
  available: true,
  writable: true,
  apply_gate: applyGateLocked,
  teams: conferenceSetupTeams,
  conferences: [conferenceBigTen, conferenceAcc, conferenceSunBelt, conferenceIndependents, conferenceCustom],
  dirty: false,
  gate_notes: [],
};

// Variant conferences for the member-list warning states.
export const conferenceAtMax = {
  ...conferenceAcc, id: 'acc-full', name: 'ACC (full)',
  teams: conferenceSetupTeams.slice(0, 6).map((t) => t.name),
  limits: { min: 4, max: 6 },
};
export const conferenceUnderMin = {
  ...conferenceAcc, id: 'acc-thin', name: 'ACC (thin)',
  teams: ['Clemson Tigers', 'Miami Hurricanes'],
  limits: { min: 4, max: 20 },
};

// Quick lookup used by the setup stories (the page builds the same map).
export const conferenceTeamsByName = Object.fromEntries(
  conferenceSetupTeams.map((t) => [t.name, t]),
);

// The game's real stadium table shape (GET /api/playoff/stadiums): stable
// index, derived name, and the game's own venue-pool tags used for grouping.
export const saveStadiums = [
  { index: 112, name: 'Mercedes-Benz Stadium', city: 'Atlanta, GA', home_of: null, pools: ['marquee', 'neutral_scheduling', 'bowl_and_neutral'] },
  { index: 11, name: 'AT&T Stadium', city: 'Arlington, TX', home_of: null, pools: ['marquee', 'neutral_scheduling', 'bowl_and_neutral'] },
  { index: 6, name: 'Allegiant Stadium', city: 'Las Vegas, NV', home_of: 'UNLV', pools: ['marquee', 'bowl_and_neutral'] },
  { index: 37, name: 'Caesars Superdome', city: 'New Orleans, LA', home_of: null, pools: ['marquee', 'bowl_and_neutral'] },
  { index: 102, name: 'Lucas Oil Stadium', city: 'Indianapolis, IN', home_of: null, pools: ['neutral_scheduling'] },
  { index: 58, name: 'Ford Field', city: 'Detroit, MI', home_of: null, pools: ['neutral_scheduling'] },
  { index: 50, name: 'EverBank Stadium', city: 'Jacksonville, FL', home_of: null, pools: ['bowl_and_neutral'] },
  { index: 3, name: 'Alamodome', city: 'San Antonio, TX', home_of: 'UTSA', pools: ['bowl_and_neutral'] },
  { index: 23, name: 'Bryant-Denny Stadium', city: null, home_of: 'Alabama', pools: [] },
  { index: 110, name: 'Memorial Stadium (Lincoln)', city: null, home_of: 'Nebraska', pools: [] },
  { index: 12, name: 'Autzen Stadium', city: null, home_of: 'Oregon', pools: [] },
  { index: 87, name: 'Ohio Stadium', city: null, home_of: 'Ohio State', pools: [] },
];

// The poll editor's entry shape (GET /api/polls -> polls.cfp / polls.ap):
// the save's full poll ordering with records and logo ids; `delta` appears on
// algorithm previews (movement vs the save's current poll).
export const pollEntries = [
  { rank: 1, row: 12, team: 'Georgia Bulldogs', school: 'Georgia', abbr: 'UGA', espn_id: 61, record: '9-0', conference: 'SEC', color: 'ba0c2f' },
  { rank: 2, row: 88, team: 'Texas Longhorns', school: 'Texas', abbr: 'TEX', espn_id: 251, record: '9-0', conference: 'SEC', color: 'bf5700' },
  { rank: 3, row: 54, team: 'Ohio State Buckeyes', school: 'Ohio State', abbr: 'OSU', espn_id: 194, record: '8-1', conference: 'Big Ten', color: 'bb0000' },
  { rank: 4, row: 71, team: 'Oregon Ducks', school: 'Oregon', abbr: 'ORE', espn_id: 2483, record: '9-0', conference: 'Big Ten', color: '154733' },
  { rank: 5, row: 33, team: 'Nebraska Cornhuskers', school: 'Nebraska', abbr: 'NEB', espn_id: 158, record: '8-1', conference: 'Big Ten', color: 'e41c38' },
  { rank: 6, row: 5, team: 'Alabama Crimson Tide', school: 'Alabama', abbr: 'ALA', espn_id: 333, record: '7-2', conference: 'SEC', color: '9e1b32' },
  { rank: 7, row: 61, team: 'Penn State Nittany Lions', school: 'Penn State', abbr: 'PSU', espn_id: 213, record: '8-1', conference: 'Big Ten', color: '041e42' },
  { rank: 8, row: 47, team: 'Ole Miss Rebels', school: 'Ole Miss', abbr: 'MISS', espn_id: 145, record: '8-1', conference: 'SEC', color: '14213d' },
  { rank: 9, row: 19, team: 'USC Trojans', school: 'USC', abbr: 'USC', espn_id: 30, record: '7-2', conference: 'Big Ten', color: '990000' },
  { rank: 10, row: 90, team: 'Miami Hurricanes', school: 'Miami', abbr: 'MIA', espn_id: 2390, record: '7-2', conference: 'ACC', color: 'f47321' },
  { rank: 11, row: 24, team: 'Oklahoma Sooners', school: 'Oklahoma', abbr: 'OU', espn_id: 201, record: '7-2', conference: 'SEC', color: '841617' },
  { rank: 12, row: 40, team: 'Louisville Cardinals', school: 'Louisville', abbr: 'LOU', espn_id: 97, record: '8-1', conference: 'ACC', color: 'ad0000' },
];

// The long-name / long-conference cases that stress the card layout (these
// collapsed the name column before the facts width was fixed).
export const pollEntriesTricky = [
  { rank: 1, row: 90, team: 'Miami Hurricanes', school: 'Miami', abbr: 'MIA', espn_id: 2390, record: '13-0', conference: 'ACC', color: 'f47321' },
  { rank: 5, row: 87, team: 'Notre Dame Fighting Irish', school: 'Notre Dame', abbr: 'ND', espn_id: 87, record: '11-1', conference: 'Independents', color: '0c2340' },
  { rank: 24, row: 152, team: 'New Mexico Lobos', school: 'New Mexico', abbr: 'UNM', espn_id: 167, record: '10-3', conference: 'Mountain West', color: 'ba0c2f' },
  { rank: 28, row: 200, team: 'North Dakota State Bison', school: 'North Dakota State', abbr: 'NDSU', espn_id: 2449, record: '9-3', conference: 'Mountain West', color: '005643' },
  { rank: 29, row: 201, team: 'Florida International Panthers', school: 'Florida International', abbr: 'FIU', espn_id: 2229, record: '9-4', conference: 'Conference USA', color: '081e3f' },
  { rank: 35, row: 202, team: 'Southern Mississippi Golden Eagles', school: 'Southern Mississippi', abbr: 'USM', espn_id: 2572, record: '8-4', conference: 'Sun Belt', color: 'ffb700' },
  { rank: 46, row: 203, team: 'Jacksonville State Gamecocks', school: 'Jacksonville State', abbr: 'JVST', espn_id: 55, record: '9-4', conference: 'Conference USA', color: 'cc0000' },
];

export const pollAlgorithms = [
  { id: 'colley', name: 'Colley Matrix', uses: 'W/L, schedule', blurb: 'Wins and losses only, adjusted for schedule strength through a linear system. Bias-free: no margins, no preseason opinion. A real BCS computer rating.' },
  { id: 'massey', name: 'Massey Ratings', uses: 'Margins, schedule', blurb: 'Least-squares ratings on point differential: every score is a statement about the two teams, solved across the whole season at once.' },
  { id: 'elo', name: 'Elo', uses: 'Margins, venue, momentum', blurb: 'Game-by-game ratings in the FiveThirtyEight style: home advantage, a margin-of-victory boost that fades for heavy favorites.' },
  { id: 'srs', name: 'Simple Rating System', uses: 'Capped margins, schedule', blurb: 'Average scoring margin plus average opponent rating, iterated until stable. The Sports-Reference standard.' },
  { id: 'bcs', name: 'BCS Formula', uses: 'Human poll + computers', blurb: "The Bowl Championship Series formula: two-thirds the human poll (the game's other poll) and one-third the computer average of the six ratings above." },
];

// A ready-to-render /api/polls response for stories (initialData).
export const pollEditorState = {
  available: true,
  poll_labels: { cfp: 'CFP Committee Rankings', ap: 'AP Top 25' },
  algorithms: pollAlgorithms,
  polls: { cfp: pollEntries, ap: pollEntries.slice().reverse().map((e, i) => ({ ...e, rank: i + 1 })) },
  // the effective ordering the rankings grid renders (here: the user's manual
  // cfp order matches the save's, and ap stays engine-ordered)
  effective: { cfp: pollEntries, ap: pollEntries.slice().reverse().map((e, i) => ({ ...e, rank: i + 1 })) },
  config: {
    polls: {
      cfp: { mode: 'manual', algorithm: 'colley', manual: pollEntries.map((e) => e.team) },
      ap: { mode: 'game', algorithm: 'colley', manual: [] },
    },
    auto_apply: true,
    last_applied: { at: '2026-11-07T21:14:03', save: 'DYNASTY-HUSKERDYNASTY', polls: ['cfp'] },
  },
  holds: { cfp: null, ap: null },
  notices: { cfp: null, ap: null },
  pending: { cfp: true, ap: false },
  games_played: 612,
  autosync: { active: true, last: null },
};

// The committee notice the backend raises once the game's own (native)
// playoff bracket is seeded and the custom automation is off: a push still
// writes, but it can only relabel seeds, never reshape the field.
export const pollNativeSealNotice =
  'the game has already set its own playoff bracket, so a committee push from '
  + 'here only relabels the seed numbers shown next to each team. The matchups '
  + 'and byes stay as the game selected them. To reshape the field, edit the '
  + 'ranking before advancing past conference championship week, or turn on '
  + 'the custom playoff and Dynasty+ will rewrite the bracket for you.';

// --- rankings hub fixtures -------------------------------------------------
// A /api/rankings/resume payload (Nebraska, mid-November shape).
const resumeOpp = (school, abbr, espnId, record, cfpRank = null, conference = 'Big Ten') => ({
  row: espnId, team: school, school, abbr, record, conference,
  espn_id: espnId, cfp_rank: cfpRank, ap_rank: cfpRank, color: null,
});

export const teamResume = {
  available: true,
  team: {
    row: 33, team: 'Nebraska Cornhuskers', school: 'Nebraska', abbr: 'NEB',
    record: '8-1', conf_record: '5-1', conference: 'Big Ten', espn_id: 158,
    color: 'e41c38', cfp_rank: 5, ap_rank: 6,
  },
  summary: {
    points_for: 312, points_against: 158, ppg: 34.7, papg: 17.6,
    avg_margin: 17.1, streak: 'W4', vs_top25: '2-1',
    home: '5-0', away: '3-1', neutral: '0-0',
  },
  games: [
    { n: 1, opponent: resumeOpp('Colorado', 'COL', 38, '4-5', null, 'Big 12'), home: true, neutral: false, result: 'W', score: '31-17', margin: 14, conference_game: false, label: null },
    { n: 2, opponent: resumeOpp('Miami', 'MIA', 2390, '7-2', 10, 'ACC'), home: false, neutral: true, result: 'W', score: '24-20', margin: 4, conference_game: false, label: 'Aer Lingus Classic' },
    { n: 3, opponent: resumeOpp('Ohio State', 'OSU', 194, '8-1', 3), home: true, neutral: false, result: 'W', score: '27-24', margin: 3, conference_game: true, label: null },
    { n: 4, opponent: resumeOpp('Penn State', 'PSU', 213, '8-1', 7), home: false, neutral: false, result: 'L', score: '13-20', margin: -7, conference_game: true, label: null },
    { n: 5, opponent: resumeOpp('Minnesota', 'MINN', 135, '5-4'), home: true, neutral: false, result: 'W', score: '38-10', margin: 28, conference_game: true, label: null },
    { n: 6, opponent: resumeOpp('Iowa', 'IOWA', 2294, '6-3'), home: false, neutral: false, result: 'W', score: '21-14', margin: 7, conference_game: true, label: null },
  ],
  best_wins: [
    { opponent: resumeOpp('Ohio State', 'OSU', 194, '8-1', 3), home: true, neutral: false, result: 'W', score: '27-24' },
    { opponent: resumeOpp('Miami', 'MIA', 2390, '7-2', 10, 'ACC'), home: false, neutral: true, result: 'W', score: '24-20' },
  ],
  worst_losses: [
    { opponent: resumeOpp('Penn State', 'PSU', 213, '8-1', 7), home: false, neutral: false, result: 'L', score: '13-20' },
  ],
  upcoming: [
    { opponent: resumeOpp('Wisconsin', 'WIS', 275, '4-5'), home: true, neutral: false, label: null },
    { opponent: resumeOpp('Michigan', 'MICH', 130, '7-2', 12), home: false, neutral: false, label: null },
  ],
};

// A second resume for the tale of the tape.
export const teamResumeB = {
  ...teamResume,
  team: {
    row: 5, team: 'Alabama Crimson Tide', school: 'Alabama', abbr: 'ALA',
    record: '7-2', conf_record: '4-2', conference: 'SEC', espn_id: 333,
    color: '9e1b32', cfp_rank: 6, ap_rank: 5,
  },
  summary: {
    points_for: 296, points_against: 190, ppg: 32.9, papg: 21.1,
    avg_margin: 11.8, streak: 'W2', vs_top25: '1-2',
    home: '5-0', away: '2-2', neutral: '0-0',
  },
  best_wins: [
    { opponent: resumeOpp('Georgia', 'UGA', 61, '9-0', 1, 'SEC'), home: true, neutral: false, result: 'W', score: '28-24' },
  ],
  worst_losses: [
    { opponent: resumeOpp('Vanderbilt', 'VAN', 238, '4-5', null, 'SEC'), home: false, neutral: false, result: 'L', score: '17-23' },
  ],
};

// A /api/rankings/scoreboard payload.
const sbSide = (school, abbr, espnId, record, cfpRank = null, team = null) => ({
  row: espnId, team: team || school, school, abbr, record,
  espn_id: espnId, cfp_rank: cfpRank, ap_rank: cfpRank, conference: null, color: null,
});

export const rankingsScoreboard = {
  available: true,
  slate: [
    { index: 1, away: sbSide('Wisconsin', 'WIS', 275, '4-5'), home: sbSide('Nebraska', 'NEB', 158, '8-1', 5, 'Nebraska Cornhuskers'), away_score: null, home_score: null, status: 'scheduled', neutral: false, conference_game: true, label: null, user: true },
    { index: 2, away: sbSide('Georgia', 'UGA', 61, '9-0', 1), home: sbSide('Texas', 'TEX', 251, '9-0', 2), away_score: null, home_score: null, status: 'scheduled', neutral: false, conference_game: true, label: null, user: false },
  ],
  recent: [
    { index: 3, away: sbSide('Ohio State', 'OSU', 194, '8-1', 3), home: sbSide('Penn State', 'PSU', 213, '8-1', 7), away_score: 31, home_score: 27, status: 'final', neutral: false, conference_game: true, label: null, user: false },
    { index: 4, away: sbSide('Miami', 'MIA', 2390, '7-2', 10), home: sbSide('Louisville', 'LOU', 97, '8-1', 12), away_score: 20, home_score: 23, status: 'final', neutral: false, conference_game: true, label: null, user: false },
    { index: 5, away: sbSide('SMU', 'SMU', 2567, '6-3'), home: sbSide('Clemson', 'CLEM', 228, '5-4'), away_score: 35, home_score: 38, status: 'final', neutral: true, conference_game: true, label: 'ACC Championship', user: false },
  ],
};

// /api/modtools/status payloads (MMC Modding Tools detection states).
const modToolsBase = {
  game_root: 'C:\Program Files (x86)\Steam\steamapps\common\College Football 27',
  anticheat_exe: 'EAAntiCheat.GameServiceLauncher.exe',
  anticheat_backup: false,
  editor_found: true,
  installed_mods: [],
  mods_dir: null,
  manager_exe: null,
  tools_path: null,
  tools_path_set: false,
};

export const modToolsStatus = {
  missing: { ...modToolsBase, tools_found: false, anticheat: 'original', ready: false },
  swapPending: {
    ...modToolsBase,
    tools_found: true,
    tools_path: '%USERPROFILE%\\Downloads\\MMC_Modding_Tools_v1.1.0.0',
    manager_exe: '%USERPROFILE%\\Downloads\\MMC_Modding_Tools_v1.1.0.0\\MMC_ModManager_v1.1.0.0\\MMCModManager.exe',
    anticheat: 'original',
    ready: false,
  },
  ready: {
    ...modToolsBase,
    tools_found: true,
    tools_path: '%USERPROFILE%\\Downloads\\MMC_Modding_Tools_v1.1.0.0',
    manager_exe: '%USERPROFILE%\\Downloads\\MMC_Modding_Tools_v1.1.0.0\\MMC_ModManager_v1.1.0.0\\MMCModManager.exe',
    mods_dir: '%USERPROFILE%\\Downloads\\MMC_Modding_Tools_v1.1.0.0\\MMC_ModManager_v1.1.0.0\\Mods\\CollegeFootball27',
    anticheat: 'stub',
    anticheat_backup: true,
    ready: true,
  },
};
modToolsStatus.readyInstalled = {
  ...modToolsStatus.ready,
  installed_mods: ['DynastyPlus Conference Logos.fbmod'],
};

// A /api/conferences/mod/export report.
export const modExportResult = {
  file: '%LOCALAPPDATA%\\DynastyPlus\\mods\\DynastyPlus Conference Logos.fbmod',
  installed_to: '%USERPROFILE%\\Downloads\\MMC_Modding_Tools_v1.1.0.0\\MMC_ModManager_v1.1.0.0\\Mods\\CollegeFootball27\\DynastyPlus Conference Logos.fbmod',
  resources: 11,
  conferences: ['Big 12', 'SEC'],
  skipped: [],
};

// /api/conferences/historic-logos "logos" payload (the game's classic
// conference marks, grouped by editor conference key).
const histLogo = (slug, tail, label) => ({
  id: `${slug}_${tail}`,
  url: `/game-assets/conferences/historic/${slug}_${tail}.png`,
  label,
});
export const historicConferenceLogos = {
  SEC: [
    histLogo('sec', '1932_1964', '1932 to 1964'),
    histLogo('sec', '1964_1966', '1964 to 1966'),
    histLogo('sec', '1966_1970', '1966 to 1970'),
    histLogo('sec', '1970_1988', '1970 to 1988'),
    histLogo('sec', '1988_2008', '1988 to 2008'),
    histLogo('sec', '2008_2022', '2008 to 2022'),
  ],
  Big_Ten: [
    histLogo('bigten', '1970_1984', '1970 to 1984'),
    histLogo('bigten', '1985_1991', '1985 to 1991'),
    histLogo('bigten', '1992_2011', '1992 to 2011'),
  ],
};

// --- Custom schedule generator (mirrors /api/schedule/setup + generate) -----
const srTeam = (row, name, school, abbr, espnId, conference, total = 12, fcs = 1) => ({
  row, name, school, abbr, espn_id: espnId, conference, total_games: total, fcs_games: fcs,
});
export const scheduleTeams = [
  srTeam(0, 'Nebraska Cornhuskers', 'Nebraska', 'NEB', 158, 'Big Ten'),
  srTeam(1, 'Ohio State Buckeyes', 'Ohio State', 'OSU', 194, 'Big Ten'),
  srTeam(2, 'Iowa Hawkeyes', 'Iowa', 'IOWA', 2294, 'Big Ten'),
  srTeam(3, 'Michigan Wolverines', 'Michigan', 'MICH', 130, 'Big Ten'),
  srTeam(4, 'Wisconsin Badgers', 'Wisconsin', 'WIS', 275, 'Big Ten'),
  srTeam(5, 'Penn State Nittany Lions', 'Penn State', 'PSU', 213, 'Big Ten'),
  srTeam(6, 'Alabama Crimson Tide', 'Alabama', 'ALA', 333, 'SEC'),
  srTeam(7, 'Georgia Bulldogs', 'Georgia', 'UGA', 61, 'SEC'),
  srTeam(8, 'Tennessee Volunteers', 'Tennessee', 'TENN', 2633, 'SEC'),
  srTeam(9, 'Auburn Tigers', 'Auburn', 'AUB', 2, 'SEC'),
  srTeam(10, 'LSU Tigers', 'LSU', 'LSU', 99, 'SEC'),
  srTeam(11, 'Texas A&M Aggies', 'Texas A&M', 'TAMU', 245, 'SEC'),
  // Independents share the save's pool name as their conference (they have no
  // rules tab), so a pair of them must still be protectable as non-con rivals.
  srTeam(12, 'Notre Dame Fighting Irish', 'Notre Dame', 'ND', 87, 'FBS Independents'),
  srTeam(13, 'UConn Huskies', 'UConn', 'CONN', 41, 'FBS Independents'),
];
export const scheduleSetupState = {
  available: true,
  writable: true,
  // a true preseason save: nothing locked, so the whole season (including
  // Week 1) regenerates; mirrors backend/schedrules._gate
  apply_gate: { ok: true, phase: 'preseason', reason: null, full_reset: true },
  user_team: scheduleTeams[0],
  user_weeks: [2, 3, 5, 6, 7, 8, 10, 11, 12, 13, 14],
  weeks: [
    { week: 1, slots: 11, locked: false }, { week: 2, slots: 91, locked: false },
    { week: 3, slots: 86, locked: false }, { week: 4, slots: 74, locked: false },
    { week: 5, slots: 71, locked: false }, { week: 6, slots: 61, locked: false },
    { week: 7, slots: 58, locked: false }, { week: 8, slots: 61, locked: false },
    { week: 9, slots: 56, locked: false }, { week: 10, slots: 55, locked: false },
    { week: 11, slots: 62, locked: false }, { week: 12, slots: 67, locked: false },
    { week: 13, slots: 69, locked: false }, { week: 14, slots: 68, locked: false },
    { week: 15, slots: 1, locked: false },
  ],
  rivalry_week: 14,
  max_noncon_rivals: 2,
  conferences: [
    {
      name: 'Big Ten', canonical: 'Big Ten',
      teams: scheduleTeams.slice(0, 6),
      games: 5, observed_games: { 5: 6 }, max_games: 5,
      rivalries: [
        { a: 'Nebraska Cornhuskers', b: 'Iowa Hawkeyes', week: 14, location: 'rotate', primary: true, name: 'Heroes Game' },
        { a: 'Ohio State Buckeyes', b: 'Michigan Wolverines', week: null, location: 'rotate', primary: false, name: null },
      ],
      round_robin_divisions: false,
      divisions: [],
    },
    {
      name: 'SEC', canonical: 'SEC',
      teams: scheduleTeams.slice(6, 12),
      games: 4, observed_games: { 4: 4, 5: 2 }, max_games: 5,
      rivalries: [
        { a: 'Alabama Crimson Tide', b: 'Tennessee Volunteers', week: 8, location: 'rotate', primary: false, name: null },
      ],
      round_robin_divisions: false,
      divisions: [['Alabama', 'Auburn', 'LSU'], ['Georgia', 'Tennessee', 'Texas A&M']],
    },
  ],
  independents: [scheduleTeams[12], scheduleTeams[13]],
  nonconference: [
    { a: 'Nebraska Cornhuskers', b: 'Alabama Crimson Tide', rank: 2, week: 3, location: 'rotate', name: null },
  ],
  // the save's own named rivalry table (saveparse/rivalries.py): known pairs
  // label their protected game automatically and suggest a name otherwise
  game_rivalries: [
    { a: 'Nebraska Cornhuskers', b: 'Iowa Hawkeyes', name: 'Heroes Game' },
    { a: 'Ohio State Buckeyes', b: 'Michigan Wolverines', name: 'The Game' },
    { a: 'Alabama Crimson Tide', b: 'Tennessee Volunteers', name: 'Third Saturday in October' },
    { a: 'Auburn Tigers', b: 'Alabama Crimson Tide', name: 'Iron Bowl' },
  ],
  feasibility: { ok: true, errors: [], warnings: [] },
  plan_ready: false,
  plan_preview: null,
};
// a Week 1 arrival save: the engine already locked the opening slate, so
// Week 1 is pinned and the gate carries the preseason guidance note
export const scheduleSetupStateWeek1Locked = {
  ...scheduleSetupState,
  apply_gate: {
    ok: true,
    phase: 'preseason',
    reason: null,
    full_reset: false,
    note: 'Week 1 already locked in this save and will keep the game\'s own matchups. To rebuild the whole season, including Week 1, apply to a save made during the preseason (before the opening week is locked), then load that save in CFB 27.',
  },
  weeks: scheduleSetupState.weeks.map((w) => (w.week === 1 ? { ...w, locked: true } : w)),
};
export const scheduleSetupStateInfeasible = {
  ...scheduleSetupState,
  feasibility: {
    ok: false,
    errors: [
      {
        code: 'conf_games_parity',
        message: 'SEC: 15 teams each playing 9 conference games needs 135 team-slots, an odd number, so some team would always be a game short.',
        fix: 'With 15 teams, use an even number of conference games (for example 8).',
        conference: 'SEC',
      },
      {
        code: 'user_bye',
        message: 'Nebraska vs Alabama is fixed for Week 4, but your team has no game slot that week in the save\'s calendar (that is one of your bye weeks).',
        fix: 'Your schedulable weeks are: 2, 3, 5, 6, 7, 8, 10, 11, 12, 13, 14.',
      },
    ],
    warnings: [
      {
        code: 'nc_parity',
        message: 'The non-conference slots across all teams do not pair up evenly; one team will end a game short unless a conference count changes.',
        fix: 'Adjust one conference\'s game count by one.',
      },
    ],
  },
};
const srPrevTeam = (t) => ({ row: t.row, school: t.school, abbr: t.abbr, espn_id: t.espn_id, fcs: false });
export const schedulePreview = {
  changed: 52, total: 66,
  weeks: [
    {
      week: 2, locked: false,
      games: [
        { away: srPrevTeam(scheduleTeams[1]), home: srPrevTeam(scheduleTeams[0]), tag: 'conference', changed: true, user: true },
        { away: srPrevTeam(scheduleTeams[7]), home: srPrevTeam(scheduleTeams[9]), tag: 'conference', changed: false, user: false },
        { away: { row: 99, school: 'FCS Midwest', abbr: 'FCS', espn_id: null, fcs: true }, home: srPrevTeam(scheduleTeams[4]), tag: 'fcs', changed: false, user: false },
      ],
    },
    {
      week: 3, locked: false,
      games: [
        { away: srPrevTeam(scheduleTeams[6]), home: srPrevTeam(scheduleTeams[0]), tag: 'rival', changed: true, user: true },
        { away: srPrevTeam(scheduleTeams[3]), home: srPrevTeam(scheduleTeams[5]), tag: 'conference', changed: true, user: false },
      ],
    },
    {
      week: 8, locked: false,
      games: [
        { away: srPrevTeam(scheduleTeams[6]), home: srPrevTeam(scheduleTeams[8]), tag: 'rivalry', changed: true, user: false },
      ],
    },
    {
      week: 14, locked: false,
      games: [
        { away: srPrevTeam(scheduleTeams[2]), home: srPrevTeam(scheduleTeams[0]), tag: 'rivalry', changed: false, user: true },
        { away: srPrevTeam(scheduleTeams[3]), home: srPrevTeam(scheduleTeams[1]), tag: 'rivalry', changed: false, user: false },
      ],
    },
  ],
};

export const bowlGameTeams = [
  { row: 1, name: 'Nebraska Cornhuskers', school: 'Nebraska', abbr: 'NEB', conference: 'Big Ten', espn_id: 158, color: '#e41c38', rank: 11, wins: 10, losses: 2, record: '10-2', bowl_eligible: true },
  { row: 2, name: 'Notre Dame Fighting Irish', school: 'Notre Dame', abbr: 'ND', conference: 'Independent', espn_id: 87, color: '#0c2340', rank: 8, wins: 10, losses: 2, record: '10-2', bowl_eligible: true },
  { row: 3, name: 'Kansas State Wildcats', school: 'Kansas State', abbr: 'KSU', conference: 'Big 12', espn_id: 2306, color: '#512888', rank: 14, wins: 9, losses: 3, record: '9-3', bowl_eligible: true },
  { row: 4, name: 'Iowa Hawkeyes', school: 'Iowa', abbr: 'IOWA', conference: 'Big Ten', espn_id: 2294, color: '#ffcd00', rank: 17, wins: 9, losses: 3, record: '9-3', bowl_eligible: true },
  { row: 5, name: 'Ole Miss Rebels', school: 'Ole Miss', abbr: 'MISS', conference: 'SEC', espn_id: 145, color: '#ce1126', rank: 19, wins: 8, losses: 4, record: '8-4', bowl_eligible: true },
  { row: 6, name: 'Miami Hurricanes', school: 'Miami', abbr: 'MIA', conference: 'ACC', espn_id: 2390, color: '#f47321', rank: 21, wins: 8, losses: 4, record: '8-4', bowl_eligible: true },
];

export const bowlGamesState = {
  available: true,
  editable: true,
  applied: false,
  year: 2027,
  status: 'selected',
  mode: 'auto',
  summary: { bowls: 3, ny6: 1, teams: 6, locked: 0, inactive: 0 },
  teams: bowlGameTeams,
  assignments: [
    { record: 928, away_row: 1, home_row: 2 },
    { record: 391, away_row: 3, home_row: 4 },
    { record: 399, away_row: 5, home_row: 6 },
  ],
  auto_assignments: [
    { record: 928, away_row: 1, home_row: 2 },
    { record: 391, away_row: 3, home_row: 4 },
    { record: 399, away_row: 5, home_row: 6 },
  ],
  games: [
    { record: 928, name: 'Rose Bowl', asset: 'rosebowl', venue: 'Rose Bowl', city: 'Pasadena, CA', ny6: true, official: false, away: bowlGameTeams[0], home: bowlGameTeams[1] },
    { record: 391, name: 'Alamo Bowl', asset: 'alamobowl', venue: 'Alamodome', city: 'San Antonio, TX', ny6: false, official: false, away: bowlGameTeams[2], home: bowlGameTeams[3] },
    { record: 399, name: 'Citrus Bowl', asset: 'citrusbowl', venue: 'Camping World Stadium', city: 'Orlando, FL', ny6: false, official: false, away: bowlGameTeams[4], home: bowlGameTeams[5] },
  ],
};
