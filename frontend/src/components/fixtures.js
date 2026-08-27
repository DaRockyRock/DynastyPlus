// Sample data for Storybook stories so domain components can be previewed in
// isolation. Shapes mirror the backend module payloads.

export const story = {
  category: 'CFP watch',
  accent: '#3b82f6',
  headline: 'Nebraska cracks the top five as the committee takes notice',
  subheadline: 'A 8-1 resume and a road upset have the Cornhuskers in the playoff conversation for real.',
  lede: 'For the first time in over a decade, Nebraska sit at No. 5 in the projected College Football Playoff field. The signature win on the road has flipped the narrative.',
  byline: 'Dana Reyes, The Press Box',
};

export const stories = [
  story,
  { category: 'Heisman watch', accent: '#eab308', headline: 'Marcus Whitfield forces his way into the Heisman race', subheadline: 'The junior is the engine of a top-five offense.', lede: 'Quietly, Whitfield has become the most efficient quarterback in the conference.', byline: 'Marcus Hale, Saturday Authority' },
  { category: 'Recruiting', accent: '#22c55e', headline: 'Five-star WR sets a visit that could swing a class', subheadline: 'Nebraska is in strong position with the cycle crown jewel on campus.', lede: 'The recruitment is reaching its crescendo with an official visit lined up.', byline: 'Theo Marsh, RecruitWire' },
];

// Structured logo references the backend tags each slider story with. Shapes mirror
// backend/modules/top_stories._attach_marks. (Prefixed to avoid clashing with the
// sim-mode team fixtures lower in this file.)
const mkNeb = { espn_id: 158, name: 'Nebraska Cornhuskers', abbr: 'NEB' };
const mkOsu = { espn_id: 194, name: 'Ohio State Buckeyes', abbr: 'OSU' };
const mkIowa = { espn_id: 2294, name: 'Iowa Hawkeyes', abbr: 'IOWA' };
const mkColo = { espn_id: 38, name: 'Colorado Buffaloes', abbr: 'COLO' };
const mkWisc = { espn_id: 275, name: 'Wisconsin Badgers', abbr: 'WIS' };
const mkOre = { espn_id: 2483, name: 'Oregon Ducks', abbr: 'ORE' };
const mkBigTen = { id: 5, name: 'Big Ten' };
const mkSec = { id: 8, name: 'SEC' };

export const matchupMarks = { kind: 'matchup', conference: mkBigTen, teams: [mkNeb, mkOsu] };
export const groupMarks = { kind: 'group', conference: mkBigTen, teams: [mkNeb, mkIowa, mkColo, mkWisc] };
export const groupSixMarks = { kind: 'group', conference: mkBigTen, teams: [mkNeb, mkOsu, mkIowa, mkColo, mkWisc, mkOre] };
export const conferenceMarks = { kind: 'conference', conference: mkSec, teams: [] };
export const teamMarks = { kind: 'team', conference: null, teams: [mkNeb] };

export const markedStories = [
  { ...story, scope: 'program', marks: { kind: 'group', conference: mkBigTen, teams: [mkNeb, mkIowa, mkColo, mkWisc] } },
  { category: 'CFP watch', accent: '#3b82f6', scope: 'program',
    headline: 'Nebraska takes down Ohio State 28-24 on the road',
    subheadline: 'A statement win flips the Big Ten East.', lede: 'The Cornhuskers handled the Buckeyes in Columbus.',
    byline: 'Dana Reyes, The Press Box', espn_id: 194, marks: matchupMarks },
  { category: 'CFP watch', accent: '#3b82f6', scope: 'national',
    headline: 'SEC race tightens at the top', subheadline: 'The conference is wide open into November.',
    lede: 'The league title chase is a sprint to December.', byline: 'Marcus Hale, Saturday Authority', marks: conferenceMarks },
];

export const article = {
  outlet: 'The Press Box', reporter: 'Dana Reyes', reliability: 93,
  category: 'CFP watch', accent: '#3b82f6',
  headline: 'Playoff picture tightens as one-loss contenders separate from the pack',
  dek: 'The committee first projection rewards strength of schedule over style points.',
  body: 'With the field down to a handful of true contenders, resume now beats reputation.\n\nTwo undefeated programs remain comfortably in front, but the margin behind them is razor thin.',
  timestamp: '2h ago',
};

export const insiderReport = {
  outlet: 'Coaching Confidential', reporter: 'Priya Anand', reliability: 64,
  category: 'Coaching carousel', accent: '#f59e0b',
  headline: 'Sources: a brand-name SEC job could open sooner than expected',
  dek: 'Donor frustration is mounting after another November fade.',
  body: 'Multiple people with knowledge of the situation describe a fan base out of patience.',
  timestamp: '3h ago', claim: 'A marquee SEC head coach will be out before bowl season.',
  confidence: 58, credibility: 64, status: 'developing',
};

export const ranking = [
  { rank: 1, team: 'Georgia Bulldogs', abbr: 'UGA', espn_id: 61, record: '9-0' },
  { rank: 2, team: 'Texas Longhorns', abbr: 'TEX', espn_id: 251, record: '9-0' },
  { rank: 3, team: 'Ohio State Buckeyes', abbr: 'OSU', espn_id: 194, record: '8-1' },
  { rank: 4, team: 'Oregon Ducks', abbr: 'ORE', espn_id: 2483, record: '9-0' },
  { rank: 5, team: 'Nebraska Cornhuskers', abbr: 'NEB', espn_id: 158, record: '8-1' },
];

export const lastResult = {
  opponent: 'Ohio State Buckeyes', opponent_abbr: 'OSU', opponent_espn_id: 194,
  home: false, result: 'W', score: '27-24', rank_matchup: '#3 Ohio State',
};

export const nextGame = {
  week: 10, opponent: 'USC Trojans', opponent_abbr: 'USC', opponent_espn_id: 30,
  opponent_record: '7-2', opponent_rank: 12, home: true,
  kickoff: 'Saturday 7:30 PM ET', tv: 'NBC / Peacock', spread: 'NEB -6.5',
};

// The save's national.scoreboard shape: every FBS game in the current week.
// lib/matchups ranks these into the marquee matchups board.
export const nationalScoreboard = [
  { week: 10,
    home: { name: 'Nebraska Cornhuskers', abbr: 'NEB', espn_id: 158, record: '8-1', rank: 5 },
    away: { name: 'USC Trojans', abbr: 'USC', espn_id: 30, record: '7-2', rank: 12 },
    conference_game: true, neutral: false, user: true,
    status: 'scheduled', home_score: null, away_score: null, line: 'NEB -6.5' },
  { week: 10,
    home: { name: 'Texas Longhorns', abbr: 'TEX', espn_id: 251, record: '9-0', rank: 2 },
    away: { name: 'Georgia Bulldogs', abbr: 'UGA', espn_id: 61, record: '9-0', rank: 1 },
    conference_game: true, neutral: false, user: false,
    status: 'scheduled', home_score: null, away_score: null, line: 'TEX -1.5' },
  { week: 10,
    home: { name: 'Penn State Nittany Lions', abbr: 'PSU', espn_id: 213, record: '8-1', rank: 7 },
    away: { name: 'Ohio State Buckeyes', abbr: 'OSU', espn_id: 194, record: '8-1', rank: 3 },
    conference_game: true, neutral: false, user: false,
    status: 'scheduled', home_score: null, away_score: null, line: 'OSU -2.5' },
  { week: 10,
    home: { name: 'LSU Tigers', abbr: 'LSU', espn_id: 99, record: '7-2', rank: 13 },
    away: { name: 'Alabama Crimson Tide', abbr: 'ALA', espn_id: 333, record: '8-1', rank: 6 },
    conference_game: true, neutral: false, user: false,
    status: 'scheduled', home_score: null, away_score: null, line: 'ALA -4' },
  { week: 10,
    home: { name: 'Northwestern Wildcats', abbr: 'NW', espn_id: 77, record: '4-5', rank: null },
    away: { name: 'Iowa Hawkeyes', abbr: 'IOWA', espn_id: 2294, record: '7-2', rank: 19 },
    conference_game: true, neutral: false, user: false,
    status: 'final', home_score: 13, away_score: 24, line: 'IOWA -7' },
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

export const committeeMember = {
  member: 'Hunter Yurachek', role: 'Committee Chair - AD, Arkansas', affiliation: 'SEC',
  conference: 'SEC', conference_id: 8, initials: 'HY', photo: null,
  bio: "Arkansas' director of athletics since 2017 and the committee chair, with prior AD stops at Houston and Coastal Carolina.",
  lens: 'As chair, drives the room toward consensus and leans on head-to-head results and quality wins.',
  justification: 'On my ballot Georgia sits at No. 1, with real separation through the first four.',
  lower_on: 'IND',
  top25: committeeBallot,
};

export const bracket = {
  byes: ranking.slice(0, 4).map((r, i) => ({ ...r, seed: i + 1 })),
  first_round: [
    { home: { ...ranking[4], seed: 5 }, away: { team: 'Indiana Hoosiers', abbr: 'IND', espn_id: 84, seed: 12 } },
    { home: { team: 'Alabama Crimson Tide', abbr: 'ALA', espn_id: 333, seed: 6 }, away: { team: 'Clemson Tigers', abbr: 'CLEM', espn_id: 228, seed: 11 } },
  ],
};

export const prospect = {
  name: 'Cam Brooks-Lee', position: 'WR', stars: 5, rating: 0.9912, hometown: 'Dallas, TX',
  leader: 'Nebraska Cornhuskers', predicted: 'Nebraska Cornhuskers', visit: 'Official visit Week 10 (USC game)',
  scouting_report: 'Smooth route runner who separates late and high-points the football.',
  analyst_takes: [
    { analyst: 'Theo Marsh', take: 'Momentum is real; Nebraska is the team to beat.' },
    { analyst: 'Bianca Ruiz', take: 'Like the film more than the ranking.' },
  ],
};

export const crystalBall = {
  prospect: 'Cam Brooks-Lee', position: 'WR', stars: 5, analyst: 'Theo Marsh',
  prediction: 'Nebraska Cornhuskers', confidence: 8, note: 'Logged a crystal ball after the latest visit chatter.',
};

export const visit = {
  prospect: 'Cam Brooks-Lee', position: 'WR', type: 'Official visit', when: 'This weekend',
  recap: 'Rolled out the red carpet for the USC game. Player-led tour and a loud night environment.',
};

export const rumor = {
  player: 'Drew Lindqvist', position: 'QB', team: 'Nebraska Cornhuskers', status: 'Expected to enter',
  confidence: 62, detail: 'Buried on the depth chart after the midseason QB decision. Likely a December entry.',
};

export const coach = {
  coach: 'Lane Whitmore', team: 'Florida Gators', abbr: 'FLA', espn_id: 57, record: '6-3',
  heat: 88, trend: 'up', note: 'Third straight November fade has the donors restless.',
};

export const candidate = {
  name: 'Ricky Salomone', current: 'Nebraska OC', archetype: 'Riser coordinator', fit: 92,
  why: 'Top-15 scoring offense, recruits the region, ready for a CEO job.',
};

export const award = {
  name: 'Heisman Trophy', criteria: 'Most outstanding player',
  candidates: [
    { name: 'Marcus Whitfield', team: 'Nebraska Cornhuskers', position: 'QB', stat_line: '2,418 yds, 22 TD', trend: 'up', blurb: 'Surging into the top tier after a road statement.' },
    { name: 'Quinn Holloway', team: 'Texas Longhorns', position: 'QB', stat_line: 'Frontrunner', trend: 'flat', blurb: 'Holds preseason equity but has not separated.' },
  ],
  notes: [{ voter: 'Dana Reyes', note: 'Moving Whitfield up. The road win was the kind of moment a ballot remembers.' }],
};

export const voter = { name: 'Dana Reyes', outlet: 'The Press Box', lean: 'rewards the best player on the best team' };

export const milestone = { season: 2026, title: 'Best start in over a decade', detail: 'Nebraska opened 8-1 and climbed to No. 5 in the CFP projection.' };
export const legacy = { player: 'Tyrell Banks', position: 'WR', years: 'SR', summary: '54 rec, 812 yds, 8 TD. Senior leader.', legacy: 'On track for the program record book' };
export const retro = { season: 2026, headline: '2026: The breakthrough is here', body: 'Nebraska have authored their best season in years at 8-1.' };
export const coachingTree = {
  head_coach: 'Garrett Mason', alma_mater: 'Nebraska', tenure: '3 seasons',
  branches: [{ name: 'Ricky Salomone', role: 'Offensive Coordinator' }, { name: 'Theo Brantley', role: 'Defensive Coordinator' }],
};

export const contact = {
  id: 'five_star_target', name: 'Cam Brooks-Lee', role: '5-star WR target', avatar: 'CB',
  category: 'Recruits', time: '9:41 AM', preview: 'appreciate the love coach, big visit this weekend',
  status: 'Official visit this weekend',
  entity: { kind: 'recruit', name: 'Cam Brooks-Lee' },
  contact_meta: { position: 'WR', stars: 5, national_rank: 8, expected_nil: 450000, stage: 'Top 3', leader: 'Nebraska Cornhuskers' },
};

export const quote = {
  speaker: 'Garrett Mason', role: 'Head Coach, Nebraska',
  text: '"USC is a complete football team and we have to be at our best for sixty minutes. Our guys have earned the right to play in these moments."',
};

export const statRows = [
  { label: 'Points per game', value: '33.4' },
  { label: 'Points allowed', value: '18.9' },
  { label: 'Total offense', value: '441.2 ypg' },
  { label: 'Turnover margin', value: '+9' },
  { label: 'Marcus Whitfield (QB)', value: '2,418 yds, 22 TD, 4 INT' },
];

export const betting = {
  game: { matchup: 'NEB vs USC', spread: 'NEB -6.5', total: 'O/U 52.5', moneyline: '-260 / +210' },
  futures: [
    { label: 'Nebraska to make the Playoff', value: '-135' },
    { label: 'Nebraska to win the conference', value: '+320' },
  ],
};

// --- NIL / Dynasty Points budget (mirrors GET /api/budget) ---
export const recruitingActions = [
  { key: 'send_the_house', label: 'Send the House', hours: 600, influence: 18, blurb: 'Full staff blitz - the biggest weekly swing you can make' },
  { key: 'schedule_visit', label: 'Set Up a Visit', hours: 250, influence: 11, blurb: 'Get the prospect on campus for a gameday' },
  { key: 'hard_sell', label: 'Hard Sell a Pitch', hours: 250, influence: 10, blurb: 'Pitch a program strength head-on' },
  { key: 'head_coach_visit', label: 'Head Coach Visit', hours: 200, influence: 9, blurb: 'You make the in-home visit personally' },
  { key: 'coordinator_visit', label: 'Coordinator Visit', hours: 150, influence: 7, blurb: 'Send a coordinator or position coach' },
  { key: 'send_dm', label: 'Send a DM', hours: 75, influence: 3, blurb: 'Low-cost touch to keep the relationship warm' },
];

export const budgetSnapshot = {
  year: 2026, week: 10, dp_per_dollar: 0.0004,
  dynasty_points: {
    total: 12000, available: 3140,
    allocations: { coaching_staff: 3800, facilities: 4000, nil: 4200 },
    committed: { coaching_staff: 3800, facilities: 4000, nil: 1060 },
  },
  nil: {
    recruiting: { pool: 5500000, committed: 0, available: 5500000 },
    roster: { pool: 5000000, committed: 2650000, available: 2350000 },
  },
  recruiting_hours: { total: 1500, spent: 0, remaining: 1500 },
  recruiting_nil: [
    { id: 'cam_brooks_lee', name: 'Cam Brooks-Lee', position: 'WR', stars: 5, expected_nil: 450000, offer: 0, floor: 0, interest: 72, stage: 'Top 3', dealbreaker: 'Brand Exposure', leader: 'Nebraska Cornhuskers', predicted: 'Nebraska Cornhuskers', committed: false },
    { id: 'marquel_henderson', name: 'Marquel Henderson', position: 'DT', stars: 4, expected_nil: 220000, offer: 250000, floor: 250000, interest: 64, stage: 'Top 3', dealbreaker: 'Playing Time', leader: 'Nebraska Cornhuskers', predicted: 'Undecided', committed: false },
    { id: 'jordan_eaves', name: 'Jordan Eaves', position: 'QB', stars: 4, expected_nil: 320000, offer: 320000, floor: 320000, interest: 96, stage: 'Hard Commit', dealbreaker: 'Playing Time', committed: true },
  ],
  roster_nil: [
    { id: 'marcus_whitfield', name: 'Marcus Whitfield', position: 'QB', year: 'JR', expected_nil: 700000, current_nil: 650000, risk_of_leaving: 28, dealbreaker: 'Brand Exposure' },
    { id: 'jaylen_ross', name: 'Jaylen Ross', position: 'CB', year: 'JR', expected_nil: 300000, current_nil: 280000, risk_of_leaving: 41, dealbreaker: 'Playing Time' },
  ],
  actions: recruitingActions,
  stages: ['Open', 'Top 5', 'Top 3', 'Verbal', 'Hard Commit'],
};

export const recruitMarker = {
  kind: 'recruit', id: 'cam_brooks_lee', name: 'Cam Brooks-Lee', expected_nil: 450000, offer: 0,
  floor: 0, interest: 72, stage: 'Top 3', dealbreaker: 'Brand Exposure', hours_remaining: 1500, hours_total: 1500,
};
export const playerMarker = {
  kind: 'player', id: 'marcus_whitfield', name: 'Marcus Whitfield', year: 'JR', position: 'QB',
  depth_chart_slot: 'Starting Quarterback', expected_nil: 700000, current_nil: 650000,
  risk_of_leaving: 28, dealbreaker: 'Brand Exposure',
};
export const budgetMarker = {
  kind: 'budget', available_dp: 3140, total_dp: 12000, recruiting_available: 5500000,
  roster_available: 2350000, hours_remaining: 1500,
};
export const offerReceipt = {
  kind: 'nil_offer', entity_kind: 'recruit', name: 'Cam Brooks-Lee', amount: 600000, expected: 450000,
  floor: 600000, dp_cost: 240, influence_delta: 9, interest: 81, stage: 'Verbal',
  message: 'You offered Cam Brooks-Lee $600K/yr (above their $450K expectation). Influence +9, now at Verbal.',
};
export const actionReceipt = {
  kind: 'recruiting_action', ok: true, name: 'Cam Brooks-Lee', action_label: 'Send the House', hours: 600,
  remaining: 900, influence_delta: 18, interest: 90, stage: 'Verbal',
  message: 'You spent recruiting hours on Cam Brooks-Lee: Send the House. Influence +18, now at Verbal.',
};

// ---- Customize studio (settings) ----
// A representative object section (Head Coach) and a list section (Roster) so
// the settings editors can be previewed without the backend.
export const settingsObjectSection = {
  key: 'head_coach', label: 'Head Coach', group: 'Program', icon: 'whistle',
  blurb: 'The face of your program.', kind: 'object', image_field: 'image',
  fields: [
    { key: 'image', label: 'Photo', type: 'image', width: 'full' },
    { key: 'name', label: 'Name', type: 'text', width: 'half' },
    { key: 'title', label: 'Title', type: 'text', width: 'half' },
    { key: 'tenure_years', label: 'Tenure (years)', type: 'number', width: 'half' },
    { key: 'hot_seat', label: 'Hot seat', type: 'percent', width: 'half' },
  ],
};
export const settingsObjectValue = {
  image: '', name: 'Garrett Mason', title: 'Head Coach', tenure_years: 3, hot_seat: 8,
};

export const settingsListSection = {
  key: 'players', label: 'Roster', group: 'People', icon: 'jersey',
  blurb: 'Your key players, their ratings, NIL, and retention risk.',
  kind: 'list', item_kind: 'Player', title_field: 'name', subtitle_field: 'position', image_field: 'image',
  fields: [
    { key: 'image', label: 'Photo', type: 'image', width: 'full' },
    { key: 'name', label: 'Name', type: 'text', width: 'half' },
    { key: 'position', label: 'Position', type: 'text', width: 'quarter' },
    { key: 'jersey', label: 'Jersey', type: 'number', width: 'quarter' },
    { key: 'rating', label: 'Overall', type: 'percent', width: 'half' },
    { key: 'note', label: 'Scouting note', type: 'textarea', width: 'full' },
  ],
};
export const settingsListItems = [
  { image: '', name: 'Marcus Whitfield', position: 'QB', jersey: 7, rating: 91, note: 'Dual-threat trigger man.' },
  { image: '', name: 'DeShawn Carter', position: 'RB', jersey: 22, rating: 88, note: 'Leads the Big Ten in rushing.' },
];

export const settingsSchema = [
  { key: 'team', label: 'Team Identity', group: 'Program', icon: 'shield', kind: 'object' },
  settingsObjectSection,
  settingsListSection,
  { key: 'reporters', label: 'Reporters', group: 'Media', icon: 'mic', kind: 'list' },
  { key: 'cfp_committee', label: 'CFP Committee', group: 'Committee', icon: 'gavel', kind: 'list' },
];

// --- Simulation / Debug mode -------------------------------------------------
export const simStatus = {
  active: true, year: 2027, week: 5, weeks_total: 12,
  user_team: 'Nebraska Cornhuskers', user_record: '3-1', user_conf_record: '1-0',
  seed: 99, teams_count: 136, has_seed: true,
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

// A normalized user-game descriptor for the override form.
export const simUserGame = {
  team: { name: 'Nebraska Cornhuskers', abbr: 'NEB', espn_id: 158 },
  opponent: { name: 'USC Trojans', abbr: 'USC', espn_id: 30 },
  home: false, week: 6,
};

// --- National recruit board --------------------------------------------------
export const recruitRows = [
  { id: 'quintrell_dupree', name: 'Quintrell Dupree', position: 'WR', position_rank: 1, stars: 5, ovr: 99,
    rating: 0.99, national_rank: 1, hometown: 'Miami, FL', state: 'FL', height: 74, weight: 192,
    expected_nil: 900000, dealbreaker: 'Brand Exposure', status: 'Committed', committed_to: 'Georgia Bulldogs',
    committed_abbr: 'UGA', committed_espn_id: 61, leader: 'Georgia Bulldogs', commit_week: 6, interest_count: 6 },
  { id: 'malik_carter', name: 'Malik Carter', position: 'CB', position_rank: 1, stars: 5, ovr: 98,
    rating: 0.98, national_rank: 2, hometown: 'Portland, OR', state: 'OR', height: 72, weight: 188,
    expected_nil: 720000, dealbreaker: 'NFL Readiness', status: 'Uncommitted', committed_to: null,
    leader: 'Oregon Ducks', leader_abbr: 'ORE', leader_espn_id: 2483, commit_week: null, interest_count: 7 },
  { id: 'zion_sorenson', name: 'Zion Sorenson', position: 'EDGE', position_rank: 3, stars: 4, ovr: 93,
    rating: 0.937, national_rank: 41, hometown: 'West Grove City, OH', state: 'OH', height: 76, weight: 250,
    expected_nil: 320000, dealbreaker: 'Coaching Stability', status: 'Signed', committed_to: 'Nebraska Cornhuskers',
    committed_abbr: 'NEB', committed_espn_id: 158, leader: 'Nebraska Cornhuskers', commit_week: 9, interest_count: 5 },
  { id: 'beau_jennings', name: 'Beau Jennings', position: 'OT', position_rank: 7, stars: 3, ovr: 84,
    rating: 0.88, national_rank: 210, hometown: 'Dalton, GA', state: 'GA', height: 78, weight: 305,
    expected_nil: 45000, dealbreaker: 'Development', status: 'Uncommitted', committed_to: null,
    leader: 'Clemson Tigers', leader_abbr: 'CLEM', leader_espn_id: 228, commit_week: null, interest_count: 4 },
];

// A completed game (Game Center) + a post-game press conference, for the
// game-center and presser component stories.
export const gameCenter = {
  game_key: '1|Nebraska Cornhuskers|Southern Miss Golden Eagles',
  week: 1, neutral: false, overtime: false, user_is_home: true,
  home: { name: 'Nebraska Cornhuskers', abbr: 'NEB', espn_id: 158, score: 31 },
  away: { name: 'Southern Miss Golden Eagles', abbr: 'USM', espn_id: 2572, score: 21 },
  final: { home_score: 31, away_score: 21, overtime: false, winner: 'Nebraska Cornhuskers' },
  team_stats: {
    home: { points: 31, total_yards: 472, pass_yards: 268, rush_yards: 204, first_downs: 24, third_down: '7-14', fourth_down: '1-1', red_zone: '4-5', turnovers: 1, sacks: 3, penalties: '5-45', time_of_possession: '32:18', plays: 71, completions: 22, attempts: 31 },
    away: { points: 21, total_yards: 355, pass_yards: 201, rush_yards: 154, first_downs: 18, third_down: '4-13', fourth_down: '1-3', red_zone: '3-4', turnovers: 2, sacks: 1, penalties: '6-52', time_of_possession: '27:42', plays: 63, completions: 18, attempts: 30 },
  },
  box: {
    home: {
      passing: [{ name: 'Marcus Whitfield', c_att: '22/31', yards: 268, td: 2, int: 1 }],
      rushing: [{ name: 'DeShawn Carter', car: 24, yards: 158, td: 2, long: 38 }, { name: 'Malik Vaughn', car: 7, yards: 46, td: 0, long: 12 }],
      receiving: [{ name: 'Tyrell Banks', rec: 7, yards: 121, td: 1, long: 44 }, { name: 'Cole Vermeer', rec: 5, yards: 63, td: 1, long: 19 }, { name: 'Brock Mercer', rec: 4, yards: 52, td: 0, long: 17 }],
      defense: [{ name: 'Big Sam Adeyemi', tackles: 7, sacks: 2, tfl: 3, int: 0, pd: 1 }, { name: 'Devin Okafor', tackles: 9, sacks: 1, tfl: 1, int: 0, pd: 0 }, { name: 'Jaylen Ross', tackles: 6, sacks: 0, tfl: 0, int: 1, pd: 2 }],
    },
    away: {
      passing: [{ name: 'Hunter Holloway', c_att: '18/30', yards: 201, td: 1, int: 1 }],
      rushing: [{ name: 'Tre Vance', car: 19, yards: 131, td: 2, long: 35 }],
      receiving: [{ name: 'Knox Mceachern', rec: 6, yards: 78, td: 1, long: 29 }, { name: 'DeShawn Fontaine', rec: 5, yards: 61, td: 0, long: 18 }],
      defense: [{ name: 'Roman Calhoun', tackles: 8, sacks: 1, tfl: 2, int: 1, pd: 1 }, { name: 'Bo Tillman', tackles: 7, sacks: 0, tfl: 0, int: 0, pd: 0 }],
    },
  },
  scoring_summary: [
    { quarter: '1', clock: '9:12', team_abbr: 'NEB', team_name: 'Nebraska Cornhuskers', type: 'TD', detail: 'Marcus Whitfield pass complete to Tyrell Banks for 44', home_score: 7, away_score: 0 },
    { quarter: '2', clock: '5:41', team_abbr: 'USM', team_name: 'Southern Miss Golden Eagles', type: 'TD', detail: 'Tre Vance rush for 12', home_score: 7, away_score: 7 },
    { quarter: '2', clock: '0:38', team_abbr: 'NEB', team_name: 'Nebraska Cornhuskers', type: 'FG', detail: 'Knox Mercer 41 yd field goal is GOOD', home_score: 10, away_score: 7 },
    { quarter: '3', clock: '7:02', team_abbr: 'NEB', team_name: 'Nebraska Cornhuskers', type: 'TD', detail: 'DeShawn Carter rush for 8', home_score: 17, away_score: 7 },
    { quarter: '3', clock: '2:15', team_abbr: 'USM', team_name: 'Southern Miss Golden Eagles', type: 'TD', detail: 'Hunter Holloway pass complete to Knox Mceachern for 12', home_score: 17, away_score: 14 },
    { quarter: '4', clock: '8:50', team_abbr: 'NEB', team_name: 'Nebraska Cornhuskers', type: 'TD', detail: 'Marcus Whitfield pass complete to Cole Vermeer for 6', home_score: 24, away_score: 14 },
    { quarter: '4', clock: '3:33', team_abbr: 'USM', team_name: 'Southern Miss Golden Eagles', type: 'TD', detail: 'Tre Vance rush for 3', home_score: 24, away_score: 21 },
    { quarter: '4', clock: '1:12', team_abbr: 'NEB', team_name: 'Nebraska Cornhuskers', type: 'TD', detail: 'DeShawn Carter rush for 22', home_score: 31, away_score: 21 },
  ],
  drives: [
    { team_abbr: 'NEB', team_name: 'Nebraska Cornhuskers', quarter: '1', start: 'OWN 25', plays: 6, yards: 75, time: '2:48', result: 'Touchdown' },
    { team_abbr: 'USM', team_name: 'Southern Miss Golden Eagles', quarter: '1', start: 'OWN 20', plays: 8, yards: 42, time: '3:30', result: 'Punt' },
    { team_abbr: 'USM', team_name: 'Southern Miss Golden Eagles', quarter: '2', start: 'OWN 32', plays: 9, yards: 68, time: '4:10', result: 'Touchdown' },
    { team_abbr: 'NEB', team_name: 'Nebraska Cornhuskers', quarter: '2', start: 'OWN 28', plays: 7, yards: 48, time: '2:02', result: 'Field Goal' },
    { team_abbr: 'NEB', team_name: 'Nebraska Cornhuskers', quarter: '3', start: 'OWN 40', plays: 5, yards: 60, time: '2:20', result: 'Touchdown' },
    { team_abbr: 'USM', team_name: 'Southern Miss Golden Eagles', quarter: '4', start: 'OWN 25', plays: 4, yards: 8, time: '1:40', result: 'Interception' },
  ],
  key_plays: [
    { quarter: '1', clock: '9:12', team_abbr: 'NEB', description: 'Marcus Whitfield pass complete to Tyrell Banks for 44, TOUCHDOWN', kind: 'TD' },
    { quarter: '4', clock: '5:01', team_abbr: 'NEB', description: 'Hunter Holloway pass INTERCEPTED by Jaylen Ross', kind: 'Turnover' },
    { quarter: '4', clock: '1:12', team_abbr: 'NEB', description: 'DeShawn Carter rush for 22, TOUCHDOWN', kind: 'TD' },
  ],
};

export const presserReporter = { id: 'reporters:tom_shatel', name: 'Tom Shatel', outlet: 'Omaha World-Herald', scope: 'local', beat: 'program', reliability: 84 };

const presserReporters = [
  presserReporter,
  { id: 'reporters:sam_mckewon', name: 'Sam McKewon', outlet: 'Omaha World-Herald', scope: 'local' },
  { id: 'reporters:parker_gabriel', name: 'Parker Gabriel', outlet: 'Lincoln Journal Star', scope: 'local' },
  { id: 'reporters:brett_vanderslice', name: 'Brett Vanderslice', outlet: 'Huskers Radio Network', scope: 'local' },
  { id: 'reporters:owen_hatcher', name: 'Owen Hatcher', outlet: 'HuskerOnline', scope: 'local' },
];

export const presser = {
  game_key: gameCenter.game_key, week: 1, opponent: 'Southern Miss Golden Eagles',
  result_line: 'W 31-21 vs Southern Miss Golden Eagles', reporters: presserReporters,
  turns: [{ reporter_id: 'reporters:tom_shatel', reporter_name: 'Tom Shatel', outlet: 'Omaha World-Herald', question: 'What was the difference for you tonight in the 31-21 win?', answer: 'Our guys executed when it mattered, and the offensive line set the tone all night.' }],
  status: 'in_progress',
  prompt: { reporter: presserReporters[1], index: 1, total: 5, kind: 'answer', question: 'Marcus Whitfield threw for 268 and two scores. How would you assess his night?' },
};

export const presserComplete = {
  ...presser, status: 'complete', prompt: null,
  turns: [
    ...presser.turns,
    { reporter_id: 'reporters:sam_mckewon', reporter_name: 'Sam McKewon', outlet: 'Omaha World-Herald', question: 'Marcus Whitfield threw for 268 and two scores. How would you assess his night?', answer: 'He was poised. He took what the defense gave him and protected the ball outside of one throw he wants back.' },
    { reporter_id: 'reporters:parker_gabriel', reporter_name: 'Parker Gabriel', outlet: 'Lincoln Journal Star', question: 'The defense forced two turnovers. What stood out on that side?', answer: 'Big Sam was disruptive up front and the secondary tackled well. That is the standard.', auto: true },
  ],
};

// --- Social feed (mirrors the backend feed module payload) ---
export const quotedPost = {
  author_name: 'ESPN College Football', handle: 'ESPNCFB', avatar: 'EC', verified: true,
  text: 'FINAL: Nebraska 31, Southern Miss 21. The Cornhuskers move to 1-0.',
};

export const feedPost = {
  id: '2026:2:espncfb:0', author_name: 'ESPN College Football', handle: 'ESPNCFB', avatar: 'EC',
  image: '', verified: true, kind: 'brand', team_espn_id: null, textable: false, text_kind: null,
  text: 'FINAL: Nebraska 31, Southern Miss 21. A clean opener for the Huskers.',
  ref: {
    type: 'game', label: 'FINAL', us: 'Nebraska', us_espn_id: 158, them: 'Southern Miss Golden Eagles',
    them_espn_id: 2572, score: '31-21', result: 'W', home: true, rank_matchup: null,
  },
  reply_to: null, quote_of: null, metrics: { likes: 2800, reposts: 410, replies: 230 },
  hours_ago: 7, ts: 999993, timestamp: '7h ago',
};

export const feedPosts = [
  feedPost,
  {
    id: '2026:2:petethamel:0', author_name: 'Pete Thamel', handle: 'petethamel', avatar: 'PT', image: '',
    verified: true, kind: 'insider', team_espn_id: null, textable: true, text_kind: 'media',
    text: 'Sources: a brand-name SEC job could open sooner than expected. Donor patience is gone after another November fade.',
    ref: {
      type: 'article', headline: 'Sources: a brand-name SEC job could open sooner than expected',
      outlet: 'ESPN', reporter: 'Pete Thamel', category: 'Coaching carousel', accent: '#f59e0b',
      article: { headline: 'Sources: a brand-name SEC job could open sooner than expected', outlet: 'ESPN', reporter: 'Pete Thamel', category: 'Coaching carousel', accent: '#f59e0b', dek: 'Donor frustration is mounting.' },
    },
    reply_to: null, quote_of: null, metrics: { likes: 4200, reposts: 980, replies: 540 },
    hours_ago: 9, ts: 999991, timestamp: '9h ago',
  },
  {
    id: '2026:2:joelklatt:0', author_name: 'Joel Klatt', handle: 'joelklatt', avatar: 'JK', image: '',
    verified: true, kind: 'personality', team_espn_id: null, textable: true, text_kind: 'media',
    text: 'Nebraska is exactly who I thought they were. That defensive front travels and it will keep them in every game this fall.',
    ref: null, reply_to: null, quote_of: null, metrics: { likes: 2688, reposts: 220, replies: 410 },
    hours_ago: 9, ts: 999991, timestamp: '9h ago',
  },
  {
    id: '2026:2:huskerdiehard42:0', author_name: 'Husker Diehard', handle: 'huskerdiehard42', avatar: 'HU', image: '',
    verified: false, kind: 'local_fan', team_espn_id: 158, textable: false, text_kind: null,
    text: 'WE ARE SO BACK. 31-21 and the defense looked nasty. believe in this team again',
    ref: null, reply_to: null, quote_of: null, metrics: { likes: 142, reposts: 8, replies: 22 },
    hours_ago: 6, ts: 999994, timestamp: '6h ago',
  },
  {
    id: '2026:2:badgersicko65:1000', author_name: 'Badger Sicko', handle: 'badgersicko65', avatar: 'BA', image: '',
    verified: false, kind: 'national_fan', team_espn_id: 275, textable: false, text_kind: null,
    text: 'huskers fans acting like beating southern miss by 10 means anything lol',
    ref: null, reply_to: null, quote_of: '2026:2:espncfb:0',
    quoted: quotedPost,
    metrics: { likes: 412, reposts: 30, replies: 64 }, hours_ago: 5, ts: 999995, timestamp: '5h ago',
  },
];

// A reporter just broke news, so this scoop is the most RECENT event (ts "now").
// It sits in the MIDDLE of the source array below, so the feed's strict
// post-time sort is what brings it (and the other posts) into recency order. The
// `breaking` flag only drives the "Breaking" tag, never the ordering.
export const breakingFeedPost = {
  id: '2026:2:adamrittenberg:0', author_name: 'Adam Rittenberg', handle: 'adamrittenberg', avatar: 'AR',
  image: '', verified: true, kind: 'insider', team_espn_id: null, textable: true, text_kind: 'media',
  text: 'Sources: Nebraska is managing a significant availability situation at running back heading into the weekend.',
  ref: {
    type: 'article', scope: 'program', headline: 'Nebraska facing a significant availability question',
    outlet: 'The Press Box', reporter: 'Adam Rittenberg', category: 'Injury', accent: '#ef4444',
    article: { headline: 'Nebraska facing a significant availability question', outlet: 'The Press Box', reporter: 'Adam Rittenberg', category: 'Injury', accent: '#ef4444', dek: 'Sources point to a notable absence as the picture comes into focus.' },
  },
  reply_to: null, quote_of: null, breaking: true,
  metrics: { likes: 5200, reposts: 1300, replies: 720 }, hours_ago: 0.02, ts: 999999.98, timestamp: 'now',
};

export const breakingFeedPosts = [
  feedPosts[0],
  feedPosts[1],
  breakingFeedPost,
  feedPosts[3],
  feedPosts[4],
];
