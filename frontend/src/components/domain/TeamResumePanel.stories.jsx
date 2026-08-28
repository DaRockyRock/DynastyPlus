import TeamResumePanel from './TeamResumePanel.jsx';
import { teamResume } from '../fixtures.js';

export default {
  title: 'Domain/TeamResumePanel',
  component: TeamResumePanel,
};

export const Default = { args: { resume: teamResume } };

export const Undefeated = {
  args: {
    resume: {
      ...teamResume,
      worst_losses: [],
      games: teamResume.games.filter((g) => g.result === 'W'),
      summary: { ...teamResume.summary, streak: 'W8', vs_top25: '2-0' },
      team: { ...teamResume.team, record: '9-0', cfp_rank: 1, ap_rank: 1 },
    },
  },
};

export const Unavailable = {
  args: { resume: { available: false, reason: 'No CFB 27 save is readable for this dynasty.' } },
};
