import FeedRefCard from './FeedRefCard.jsx';

export default { title: 'Phone/FeedRefCard', component: FeedRefCard, parameters: { layout: 'centered' } };

const wrap = (child) => <div style={{ width: 340, background: '#000', padding: 14, borderRadius: 12 }}>{child}</div>;

export const GameFinal = {
  render: () => wrap(<FeedRefCard refData={{ type: 'game', label: 'FINAL', us: 'Nebraska', us_espn_id: 158, them: 'USC Trojans', them_espn_id: 30, score: '31-24', result: 'W', rank_matchup: 'No. 12 USC' }} />),
};

export const Article = {
  render: () => wrap(<FeedRefCard
    refData={{ type: 'article', headline: 'Sources: a brand-name SEC job could open sooner than expected', outlet: 'ESPN', reporter: 'Pete Thamel', category: 'Coaching carousel', accent: '#f59e0b', article: { headline: 'x' } }}
    onOpenArticle={() => alert('open reader')}
  />),
};

export const Ranking = {
  render: () => wrap(<FeedRefCard refData={{ type: 'ranking', label: 'AP Top 25', items: [
    { rank: 1, team: 'Penn State Nittany Lions', espn_id: 213 },
    { rank: 2, team: 'Georgia Bulldogs', espn_id: 61 },
    { rank: 3, team: 'Ohio State Buckeyes', espn_id: 194 },
  ] }} />),
};

export const Recruit = {
  render: () => wrap(<FeedRefCard refData={{ type: 'recruit', name: 'Cam Brooks-Lee', position: 'WR', stars: 5, status: 'target', hometown: 'Frisco, TX', interest: 78, leader: 'Nebraska' }} />),
};

export const ConferenceRace = {
  render: () => wrap(<FeedRefCard refData={{ type: 'confrace', label: 'Big Ten race', teams: [
    { team: 'Ohio State Buckeyes', espn_id: 194, overall: '4-0' },
    { team: 'Oregon Ducks', espn_id: 2483, overall: '4-0' },
    { team: 'Michigan Wolverines', espn_id: 130, overall: '3-1' },
  ] }} />),
};
