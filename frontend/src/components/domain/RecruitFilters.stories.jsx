import { useState } from 'react';
import RecruitFilters from './RecruitFilters.jsx';

export default {
  title: 'Domain/RecruitFilters',
  component: RecruitFilters,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => {
    const [value, setValue] = useState({ q: '', position: '', stars: '0', status: 'all' });
    return <div style={{ width: 760 }}><RecruitFilters value={value} onChange={setValue} count={700} /></div>;
  },
};
