import { useState } from 'react';
import RecruitBoard from './RecruitBoard.jsx';
import { recruitRows } from '../fixtures.js';

export default {
  title: 'Domain/RecruitBoard',
  component: RecruitBoard,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => {
    const [sort, setSort] = useState({ key: 'national_rank', dir: 1 });
    return (
      <div style={{ width: 760 }}>
        <RecruitBoard recruits={recruitRows} sort={sort} onSort={(key) => setSort({ key, dir: 1 })} />
      </div>
    );
  },
};

export const Empty = { render: () => <div style={{ width: 760 }}><RecruitBoard recruits={[]} /></div> };
