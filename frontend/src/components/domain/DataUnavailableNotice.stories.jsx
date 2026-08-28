import DataUnavailableNotice from './DataUnavailableNotice.jsx';

export default {
  title: 'Domain/DataUnavailableNotice',
  component: DataUnavailableNotice,
};

export const Committee = {
  args: {
    title: 'Committee not available yet',
    data: { unavailable: true, reason: 'Scores, rankings, and the national picture are not in the CFB 27 save yet.' },
  },
};

export const Recruiting = {
  args: {
    title: 'Recruiting board not available yet',
    data: { unavailable: true, reason: 'Recruiting boards are not in the CFB 27 save yet.' },
  },
};

export const BowlSchedule = {
  args: {
    title: 'Bowl schedule not available yet',
    data: { unavailable: true, reason: 'The postseason bowl records are not available at this point in the season.' },
  },
};
