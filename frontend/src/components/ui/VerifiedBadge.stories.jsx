import VerifiedBadge from './VerifiedBadge.jsx';

export default { title: 'UI/VerifiedBadge', component: VerifiedBadge, parameters: { layout: 'centered' } };

export const Verified = {
  render: () => (
    <div style={{ display: 'flex', gap: 16, alignItems: 'center', color: '#fff' }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>ESPN <VerifiedBadge /></span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>Big <VerifiedBadge size={18} /></span>
    </div>
  ),
};

export const Unverified = {
  render: () => (
    <span style={{ color: '#fff', display: 'inline-flex', gap: 5 }}>
      Some Fan <VerifiedBadge verified={false} />
    </span>
  ),
};
