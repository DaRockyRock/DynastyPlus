import RankingList, { RankRow } from './RankingList.jsx';
import Card from '../ui/Card.jsx';
import { ranking } from '../fixtures.js';

export default {
  title: 'Domain/RankingList',
  component: RankingList,
  parameters: { layout: 'padded' },
};

export const CFPTop = {
  render: () => (
    <Card className="panel" style={{ width: 340 }}>
      <RankingList teams={ranking} userTeam="Nebraska Cornhuskers" />
    </Card>
  ),
};

export const SingleRow = {
  render: () => (
    <Card className="panel" style={{ width: 340 }}>
      <RankRow row={ranking[4]} isUser />
    </Card>
  ),
};
