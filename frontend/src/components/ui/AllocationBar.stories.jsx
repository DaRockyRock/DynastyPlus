import AllocationBar from './AllocationBar.jsx';

export default {
  title: 'UI/AllocationBar',
  component: AllocationBar,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => (
    <div style={{ width: 460 }}>
      <AllocationBar total={12000} allocations={{ coaching_staff: 3800, facilities: 4000, nil: 4200 }} />
    </div>
  ),
};

export const WithOpenRoom = {
  render: () => (
    <div style={{ width: 460 }}>
      <AllocationBar total={12000} allocations={{ coaching_staff: 3000, facilities: 3000, nil: 4000 }} />
    </div>
  ),
};
