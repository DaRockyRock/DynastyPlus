import NilCallout from './NilCallout.jsx';

export default {
  title: 'UI/NilCallout',
  component: NilCallout,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => (
    <div style={{ maxWidth: 460 }}>
      <NilCallout>
        The collective restructured deals for two rising sophomores to head off poaching, betting
        that continuity is worth more than chasing splashy outside additions.
      </NilCallout>
    </div>
  ),
};
