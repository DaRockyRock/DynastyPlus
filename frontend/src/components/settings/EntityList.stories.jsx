import { useState } from 'react';
import EntityList from './EntityList.jsx';
import { settingsListSection, settingsListItems } from '../fixtures.js';

export default {
  title: 'Settings/EntityList',
  component: EntityList,
  parameters: { layout: 'padded' },
};

export const Roster = {
  render: () => {
    const [items, setItems] = useState(settingsListItems);
    return <div style={{ maxWidth: 760 }}><EntityList section={settingsListSection} items={items} onChange={setItems} /></div>;
  },
};

export const Empty = {
  render: () => {
    const [items, setItems] = useState([]);
    return <div style={{ maxWidth: 760 }}><EntityList section={settingsListSection} items={items} onChange={setItems} /></div>;
  },
};
