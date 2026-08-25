// Sample Dynasty+ Tools data for isolated Storybook previews.

export const recruitingActions = [
  { key: 'send_the_house', label: 'Send the House', hours: 600, influence: 18, blurb: 'Full staff blitz' },
  { key: 'schedule_visit', label: 'Set Up a Visit', hours: 250, influence: 11, blurb: 'Bring the prospect to campus' },
  { key: 'hard_sell', label: 'Hard Sell a Pitch', hours: 250, influence: 10, blurb: 'Pitch a program strength' },
];

export const budgetSnapshot = {
  year: 2026,
  week: 10,
  dp_per_dollar: 0.0004,
  dynasty_points: {
    total: 12000,
    available: 3140,
    allocations: { coaching_staff: 3800, facilities: 4000, nil: 4200 },
    committed: { coaching_staff: 3800, facilities: 4000, nil: 1060 },
  },
  nil: {
    recruiting: { pool: 5500000, committed: 0, available: 5500000 },
    roster: { pool: 5000000, committed: 2650000, available: 2350000 },
  },
  recruiting_hours: { total: 1500, spent: 0, remaining: 1500 },
  recruiting_nil: [
    { id: 'cam_brooks_lee', name: 'Cam Brooks-Lee', position: 'WR', stars: 5, expected_nil: 450000, offer: 0, floor: 0, interest: 72, stage: 'Top 3', dealbreaker: 'Brand Exposure', leader: 'Nebraska Cornhuskers', committed: false },
    { id: 'marquel_henderson', name: 'Marquel Henderson', position: 'DT', stars: 4, expected_nil: 220000, offer: 250000, floor: 250000, interest: 64, stage: 'Top 3', dealbreaker: 'Playing Time', leader: 'Nebraska Cornhuskers', committed: false },
    { id: 'jordan_eaves', name: 'Jordan Eaves', position: 'QB', stars: 4, expected_nil: 320000, offer: 320000, floor: 320000, interest: 96, stage: 'Hard Commit', dealbreaker: 'Playing Time', committed: true },
  ],
  roster_nil: [
    { id: 'marcus_whitfield', name: 'Marcus Whitfield', position: 'QB', year: 'JR', expected_nil: 700000, current_nil: 650000, risk_of_leaving: 28, dealbreaker: 'Brand Exposure' },
    { id: 'jaylen_ross', name: 'Jaylen Ross', position: 'CB', year: 'JR', expected_nil: 300000, current_nil: 280000, risk_of_leaving: 41, dealbreaker: 'Playing Time' },
  ],
  actions: recruitingActions,
  stages: ['Open', 'Top 5', 'Top 3', 'Verbal', 'Hard Commit'],
};

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
  blurb: 'Your players, ratings, NIL, and retention risk.',
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
  { image: '', name: 'DeShawn Carter', position: 'RB', jersey: 22, rating: 88, note: 'Leads the conference in rushing.' },
];

export const settingsSchema = [
  { key: 'team', label: 'Team Identity', group: 'Program', icon: 'shield', kind: 'object' },
  settingsObjectSection,
  settingsListSection,
];

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
  { week: 5, home: neb, away: ore, conference: false, neutral: false, user: true, status: 'final', home_score: 31, away_score: 27, override: false, winner: 'Nebraska Cornhuskers' },
  { week: 5, home: osu, away: mich, conference: true, neutral: false, user: false, status: 'final', home_score: 24, away_score: 21, override: false, winner: 'Ohio State Buckeyes' },
  { week: 5, home: iowa, away: { name: 'Wisconsin Badgers', abbr: 'WIS', espn_id: 275, rating: 74, is_user: false, rank: null }, conference: true, neutral: false, user: false, status: 'final', home_score: 17, away_score: 20, override: false, winner: 'Wisconsin Badgers' },
];

export const scoreboardUpcoming = [
  { week: 6, home: { name: 'USC Trojans', abbr: 'USC', espn_id: 30, rating: 80, is_user: false, rank: 12 }, away: neb, conference: true, neutral: false, user: true, status: 'scheduled', home_score: null, away_score: null, override: false, winner: null },
];

export const simUserGame = {
  team: { name: 'Nebraska Cornhuskers', abbr: 'NEB', espn_id: 158 },
  opponent: { name: 'USC Trojans', abbr: 'USC', espn_id: 30 },
  home: false,
  week: 6,
};

export const recruitRows = [
  { id: 'quintrell_dupree', name: 'Quintrell Dupree', position: 'WR', position_rank: 1, stars: 5, ovr: 99, rating: 0.99, national_rank: 1, hometown: 'Miami, FL', state: 'FL', expected_nil: 900000, dealbreaker: 'Brand Exposure', status: 'Committed', committed_to: 'Georgia Bulldogs', committed_abbr: 'UGA', committed_espn_id: 61, leader: 'Georgia Bulldogs' },
  { id: 'malik_carter', name: 'Malik Carter', position: 'CB', position_rank: 1, stars: 5, ovr: 98, rating: 0.98, national_rank: 2, hometown: 'Portland, OR', state: 'OR', expected_nil: 720000, dealbreaker: 'NFL Readiness', status: 'Uncommitted', committed_to: null, leader: 'Oregon Ducks', leader_abbr: 'ORE' },
  { id: 'zion_sorenson', name: 'Zion Sorenson', position: 'EDGE', position_rank: 3, stars: 4, ovr: 93, rating: 0.937, national_rank: 41, hometown: 'West Grove City, OH', state: 'OH', expected_nil: 320000, dealbreaker: 'Coaching Stability', status: 'Signed', committed_to: 'Nebraska Cornhuskers', committed_abbr: 'NEB', committed_espn_id: 158, leader: 'Nebraska Cornhuskers' },
  { id: 'beau_jennings', name: 'Beau Jennings', position: 'OT', position_rank: 7, stars: 3, ovr: 84, rating: 0.88, national_rank: 210, hometown: 'Dalton, GA', state: 'GA', expected_nil: 45000, dealbreaker: 'Development', status: 'Uncommitted', committed_to: null, leader: 'Clemson Tigers', leader_abbr: 'CLEM' },
];
