import RankingsHubPanel from './RankingsHubPanel.jsx';
import { pollEditorState, rankingsScoreboard, teamResume, teamResumeB } from '../fixtures.js';

export default {
  title: 'Domain/RankingsHubPanel',
  component: RankingsHubPanel,
};

const resumeFn = async (row) => (row === 5 ? teamResumeB : teamResume);

export const Default = {
  args: {
    initialData: pollEditorState,
    scoreboardData: rankingsScoreboard,
    resumeFn,
    userTeam: 'Nebraska Cornhuskers',
  },
};

export const NoSave = {
  args: {
    initialData: { available: false, reason: 'No CFB 27 save was found. Scan a dynasty first.' },
  },
};
