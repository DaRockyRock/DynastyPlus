import WeekScoreboardPanel from './WeekScoreboardPanel.jsx';
import { rankingsScoreboard } from '../fixtures.js';

export default {
  title: 'Domain/WeekScoreboardPanel',
  component: WeekScoreboardPanel,
};

export const Default = {
  args: { data: rankingsScoreboard, userTeam: 'Nebraska Cornhuskers' },
};

export const Unavailable = {
  args: { data: { available: false, reason: 'No CFB 27 save is readable for this dynasty.' } },
};
