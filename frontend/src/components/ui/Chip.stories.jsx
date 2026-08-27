import Chip from './Chip.jsx';
import { CATEGORY_COLORS } from '../../lib/categories.js';

export default {
  title: 'UI/Chip',
  component: Chip,
  parameters: { layout: 'centered' },
};

export const CFPWatch = { args: { category: 'CFP watch' } };
export const Recruiting = { args: { category: 'Recruiting' } };
export const CustomAccent = { args: { category: 'Breaking', accent: '#ec4899' } };

export const AllCategories = {
  render: () => (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, maxWidth: 460 }}>
      {Object.keys(CATEGORY_COLORS).map((c) => (
        <Chip key={c} category={c} />
      ))}
    </div>
  ),
};
