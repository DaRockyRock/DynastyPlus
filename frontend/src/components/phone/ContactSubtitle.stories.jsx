import ContactSubtitle from './ContactSubtitle.jsx';

const wrap = (contact) => (
  <div style={{ background: '#000', padding: '12px 16px', width: 340, borderRadius: 8 }}>
    <ContactSubtitle contact={contact} />
  </div>
);

export default { title: 'Phone/ContactSubtitle', component: ContactSubtitle };

export const RecruitLeader = {
  render: () => wrap({
    category: 'Recruits',
    entity: { kind: 'recruit' },
    contact_meta: { position: 'WR', stars: 5, national_rank: 8, expected_nil: 450000, stage: 'Top 3', leader: 'Nebraska Cornhuskers' },
  }),
};

export const RecruitTrailing = {
  render: () => wrap({
    category: 'Recruits',
    entity: { kind: 'recruit' },
    contact_meta: { position: 'S', stars: 4, national_rank: 44, expected_nil: 180000, stage: 'Top 5', leader: 'Oregon Ducks' },
  }),
};

export const Player = {
  render: () => wrap({
    category: 'Players',
    entity: { kind: 'player' },
    contact_meta: { position: 'QB', depth_chart_slot: 'Starting Quarterback', current_nil: 650000 },
  }),
};

export const StaffCoach = {
  render: () => wrap({
    category: 'Staff',
    role: 'Offensive Coordinator',
    entity: { kind: 'staff' },
  }),
};

export const StaffAD = {
  render: () => wrap({
    category: 'Staff',
    role: 'Athletic Director',
    entity: { kind: 'budget' },
    contact_meta: { school: 'Nebraska' },
  }),
};

export const MediaNational = {
  render: () => wrap({
    category: 'Media',
    media_scope: 'National',
    media_type: 'personality',
    outlet: 'Coaching Confidential',
    entity: { kind: 'none' },
  }),
};

export const MediaLocal = {
  render: () => wrap({
    category: 'Media',
    media_scope: 'Local',
    media_type: 'writer',
    outlet: 'Cornhusker Insider',
    entity: { kind: 'none' },
  }),
};

// Any other category (an opposing coach, a carousel candidate) falls back to the
// plain role so the contact still names who they are.
export const OpposingCoach = {
  render: () => wrap({
    category: 'Coaches',
    role: 'Head Coach, Florida Gators',
    entity: { kind: 'none' },
  }),
};
