import InboxDrainPanel from './InboxDrainPanel.jsx';

export default {
  title: 'Domain/InboxDrainPanel',
  component: InboxDrainPanel,
  parameters: { layout: 'padded' },
};

const actions = [
  { id: '1', kind: 'nil_offer', entity_id: 'cam_brooks_lee', amount: 450000, week: 6, applied: false },
  { id: '2', kind: 'recruiting_action', entity_id: 'marquel_henderson', action_key: 'send_the_house', week: 6, applied: false },
  { id: '3', kind: 'allocate', week: 6, applied: false },
];

export const Empty = { render: () => <div style={{ width: 520 }}><InboxDrainPanel actions={[]} /></div> };
export const Queued = { render: () => <div style={{ width: 520 }}><InboxDrainPanel actions={actions} /></div> };
