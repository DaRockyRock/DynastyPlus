import { useState } from 'react';
import EntityCard from './EntityCard.jsx';
import { settingsListSection, settingsListItems } from '../fixtures.js';

export default {
  title: 'Settings/EntityCard',
  component: EntityCard,
  parameters: { layout: 'padded' },
};

function Demo({ open: initialOpen }) {
  const [item, setItem] = useState(settingsListItems[0]);
  const [open, setOpen] = useState(initialOpen);
  return (
    <div style={{ maxWidth: 760 }}>
      <EntityCard
        section={settingsListSection}
        item={item}
        index={0}
        total={2}
        open={open}
        onToggle={() => setOpen((o) => !o)}
        onChange={setItem}
        onRemove={() => {}}
        onDuplicate={() => {}}
        onMoveUp={() => {}}
        onMoveDown={() => {}}
      />
    </div>
  );
}

export const Collapsed = { render: () => <Demo open={false} /> };
export const Expanded = { render: () => <Demo open /> };
