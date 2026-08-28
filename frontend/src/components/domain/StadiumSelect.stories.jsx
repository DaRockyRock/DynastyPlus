import { useState } from 'react';
import StadiumSelect from './StadiumSelect.jsx';
import { saveStadiums } from '../fixtures.js';

export default {
  title: 'Domain/StadiumSelect',
  component: StadiumSelect,
};

function Demo({ initial = null }) {
  const [value, setValue] = useState(initial);
  const [picked, setPicked] = useState(null);
  return (
    <div style={{ width: 420, display: 'grid', gap: 10 }}>
      <StadiumSelect
        stadiums={saveStadiums}
        value={value}
        onPick={(s) => { setValue(s ? s.index : null); setPicked(s); }}
      />
      <div style={{ color: 'var(--ink-dim, #9aa7b4)', fontSize: 13 }}>
        {picked ? `${picked.name}${picked.city ? `, ${picked.city}` : ''}` : 'Nothing picked yet'}
      </div>
    </div>
  );
}

export const Empty = { render: () => <Demo /> };
export const Preselected = { render: () => <Demo initial={112} /> };
