import SectionTitle from './SectionTitle.jsx';
import Button from './Button.jsx';

export default {
  title: 'UI/SectionTitle',
  component: SectionTitle,
  parameters: { layout: 'padded' },
};

export const Plain = { args: { children: 'Recruiting Board' } };

export const WithRight = {
  render: () => (
    <div style={{ width: 520 }}>
      <SectionTitle right={<Button>Adjust</Button>}>
        NIL Allocation
      </SectionTitle>
    </div>
  ),
};

export const WithNote = {
  render: () => (
    <div style={{ width: 520 }}>
      <SectionTitle note="Sorted by national rank">Top Prospects</SectionTitle>
    </div>
  ),
};
