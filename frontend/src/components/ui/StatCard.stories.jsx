import StatCard from './StatCard.jsx';

export default {
  title: 'UI/StatCard',
  component: StatCard,
  parameters: { layout: 'centered' },
};

export const Scoring = {
  args: { label: 'Scoring Offense', value: '33.4', unit: 'ppg', nationalRank: 12, confRank: 3, conference: 'Big Ten' },
};

export const TurnoverMargin = {
  args: { label: 'Turnover Margin', value: '+9', nationalRank: 5, confRank: 1, conference: 'Big Ten' },
};

export const Grid = {
  render: () => (
    <div className="stat-cards" style={{ width: 340 }}>
      <StatCard label="Scoring Offense" value="33.4" unit="ppg" nationalRank={12} confRank={3} conference="Big Ten" />
      <StatCard label="Scoring Defense" value="18.9" unit="ppg" nationalRank={9} confRank={2} conference="Big Ten" />
      <StatCard label="Total Offense" value="441.2" unit="ypg" nationalRank={15} confRank={4} conference="Big Ten" />
      <StatCard label="Turnover Margin" value="+9" nationalRank={5} confRank={1} conference="Big Ten" />
    </div>
  ),
};
