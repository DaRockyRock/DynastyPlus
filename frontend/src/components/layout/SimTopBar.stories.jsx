import SimTopBar from './SimTopBar.jsx';
import { simStatus } from '../fixtures.js';

export default {
  title: 'Layout/SimTopBar',
  component: SimTopBar,
  parameters: { layout: 'fullscreen' },
};

const team = { name: 'Nebraska Cornhuskers', abbreviation: 'NEB', espn_id: 158, color: 'e41c38', alt_color: 'f5f5f5', logo: '' };

export const Active = { render: () => <SimTopBar team={team} sim={simStatus} pending={0} /> };
export const WithQueuedActions = { render: () => <SimTopBar team={team} sim={simStatus} pending={3} onClick={() => {}} /> };
export const NoSeason = { render: () => <SimTopBar team={team} sim={{ active: false }} pending={0} /> };
