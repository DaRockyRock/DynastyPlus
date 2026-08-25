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
        title="Season"
        sub="Start and step through a modeled college football season"
        actions={<Button>Reset Season</Button>}
      />
    </div>
  ),
};
