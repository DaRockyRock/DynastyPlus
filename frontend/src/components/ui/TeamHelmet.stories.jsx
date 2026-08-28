import TeamHelmet from './TeamHelmet.jsx';

export default {
  title: 'UI/TeamHelmet',
  component: TeamHelmet,
};

export const FacingRight = {
  args: { espnId: 2429, name: 'Charlotte 49ers', abbr: 'CLT', side: 'right', size: 140 },
};

export const FacingLeft = {
  args: { espnId: 99, name: 'LSU Tigers', abbr: 'LSU', side: 'left', size: 140 },
};

export const MonogramFallback = {
  args: { espnId: null, name: 'Mystery Team', abbr: 'MT', color: '#046a38', size: 100 },
};
