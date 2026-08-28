import WeekNav from './WeekNav.jsx';

export default {
  title: 'Layout/WeekNav',
  component: WeekNav,
  parameters: { layout: 'centered' },
};

export const MidSeason = { args: { week: 10 } };
export const FirstWeek = { args: { week: 1 } };
