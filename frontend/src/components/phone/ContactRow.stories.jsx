import ContactRow from './ContactRow.jsx';

const contacts = [
  {
    id: 'cam', name: 'Cam Brooks-Lee', avatar: 'CB', time: '9:41 AM',
    category: 'Recruits', entity: { kind: 'recruit', name: 'Cam Brooks-Lee' },
    preview: 'appreciate the love coach, big visit this weekend',
    contact_meta: { position: 'WR', stars: 5, national_rank: 8, expected_nil: 450000, stage: 'Top 3', leader: 'Nebraska Cornhuskers' },
  },
  {
    id: 'antoine', name: 'Antoine Devereaux', avatar: 'AD', time: 'Yesterday',
    category: 'Recruits', entity: { kind: 'recruit', name: 'Antoine Devereaux' },
    preview: 'took my official to Oregon last weekend, still deciding',
    contact_meta: { position: 'S', stars: 4, national_rank: 44, expected_nil: 180000, stage: 'Top 5', leader: 'Oregon Ducks' },
  },
  {
    id: 'qb', name: 'Marcus Whitfield', avatar: 'MW', time: '7:55 AM',
    category: 'Players', entity: { kind: 'player', name: 'Marcus Whitfield' },
    preview: 'all good coach. just focused on the game plan.',
    contact_meta: { position: 'QB', depth_chart_slot: 'Starting Quarterback', current_nil: 650000 },
  },
  {
    id: 'oc', name: 'Coach Salomone', avatar: 'RS', time: '8:12 AM',
    category: 'Staff', role: 'Offensive Coordinator', entity: { kind: 'staff' },
    preview: 'tempo plan is dialed for Saturday. we push the pace early.',
  },
  {
    id: 'ad', name: 'Athletic Director', avatar: 'AD', time: 'Sun',
    category: 'Staff', role: 'Athletic Director', entity: { kind: 'budget' },
    preview: 'the trajectory speaks for itself. lets keep building.',
    contact_meta: { school: 'Nebraska' },
  },
  {
    id: 'insider', name: 'Priya Anand', avatar: 'PA', time: '10:20 AM',
    category: 'Media', entity: { kind: 'none' },
    media_scope: 'National', media_type: 'personality', outlet: 'Coaching Confidential',
    preview: 'hearing things on that job we talked about...',
  },
];

export default { title: 'Phone/ContactRow', component: ContactRow, parameters: { layout: 'centered' } };

export const List = {
  render: () => (
    <div style={{ width: 372, background: '#000', borderRadius: 16, padding: '8px 0' }}>
      {contacts.map((c) => <ContactRow key={c.id} contact={c} />)}
    </div>
  ),
};

// People text the coach first week to week; unread rows carry a blue dot and
// bolder text until he opens the conversation.
export const WithUnread = {
  render: () => (
    <div style={{ width: 372, background: '#000', borderRadius: 16, padding: '8px 0' }}>
      <ContactRow contact={{ ...contacts[0], preview: 'coach we might need to talk soon', time: 'Wk 10' }} unread={2} />
      <ContactRow contact={{ ...contacts[3], preview: 'got an update on one of our targets', time: 'Wk 10' }} unread={1} />
      <ContactRow contact={contacts[1]} />
    </div>
  ),
};

// While a contact composes a reply (LLM generating), the row shows a live typing
// indicator even after the coach leaves the conversation.
export const Typing = {
  render: () => (
    <div style={{ width: 372, background: '#000', borderRadius: 16, padding: '8px 0' }}>
      <ContactRow contact={{ ...contacts[0], time: 'now' }} typing />
      <ContactRow contact={contacts[2]} />
    </div>
  ),
};
