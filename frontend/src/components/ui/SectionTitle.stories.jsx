import SectionTitle from './SectionTitle.jsx';
import Button from './Button.jsx';

export default {
  title: 'UI/SectionTitle',
  component: SectionTitle,
  parameters: { layout: 'padded' },
};

export const Plain = { args: { children: 'Protected Rivalries' } };

export const WithRight = {
  render: () => (
    <div style={{ width: 520 }}>
      <SectionTitle right={<Button variant="regen">Reset</Button>}>
        Conference Rules
      </SectionTitle>
    </div>
  ),
};

export const WithNote = {
  render: () => (
    <div style={{ width: 520 }}>
      <SectionTitle note="Generated from the active save">Schedule Preview</SectionTitle>
    </div>
  ),
};
