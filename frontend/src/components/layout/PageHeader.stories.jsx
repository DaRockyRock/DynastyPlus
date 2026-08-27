import PageHeader from './PageHeader.jsx';
import SourcePill from '../ui/SourcePill.jsx';
import RegenerateButton from '../ui/RegenerateButton.jsx';

export default {
  title: 'Layout/PageHeader',
  component: PageHeader,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => (
    <div style={{ width: 760 }}>
      <PageHeader
        title="News Feed"
        sub="National and program coverage from across the dynasty media universe"
        actions={<><SourcePill source="mock" /><RegenerateButton /></>}
      />
    </div>
  ),
};
