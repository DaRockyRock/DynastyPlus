import PageHeader from './PageHeader.jsx';
import Button from '../ui/Button.jsx';

export default {
  title: 'Layout/PageHeader',
  component: PageHeader,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => (
    <div style={{ width: 760 }}>
      <PageHeader
        title="Conference Setup"
        sub="Edit membership, divisions, rivalries, and conference identity."
        actions={<Button variant="accent">Save Changes</Button>}
      />
    </div>
  ),
};
