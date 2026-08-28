import HelmetMatchup from './HelmetMatchup.jsx';

export default {
  title: 'Domain/HelmetMatchup',
  component: HelmetMatchup,
};

export const RivalryWeek = {
  args: {
    away: { espn_id: 2429, name: 'Charlotte', abbr: 'CLT', record: '1-1 (0-0)' },
    home: { espn_id: 2026, name: 'App St.', abbr: 'APP', record: '2-0 (0-0)' },
    size: 130,
  },
};

export const CompactNoNames = {
  args: {
    away: { espn_id: 99, name: 'LSU', abbr: 'LSU' },
    home: { espn_id: 145, name: 'Ole Miss', abbr: 'MISS' },
    size: 72,
    showNames: false,
    mark: 'VS',
  },
};
