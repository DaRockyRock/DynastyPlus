import PersonName from './PersonName.jsx';

// PersonName reads textPerson from AppContext; in Storybook there is no provider,
// so we pass an `onText` override that just reports the resolved descriptor.
const onText = (p) => alert(`Text ${p.name} (kind: ${p.kind || 'unknown'})`);

export default {
  title: 'People/PersonName',
  component: PersonName,
  parameters: { layout: 'centered' },
  args: { onText },
};

export const Recruit = {
  args: { name: 'Cam Brooks-Lee', kind: 'recruit' },
  render: (args) => (
    <div style={{ fontFamily: 'Saira, sans-serif', fontSize: 16, color: 'var(--text, #eef2f7)' }}>
      <b><PersonName {...args} /></b>
    </div>
  ),
};

export const OpposingCoach = {
  args: { name: 'Lane Whitmore', kind: 'opp_coach', team: 'Florida Gators' },
  render: (args) => (
    <div style={{ fontSize: 16, color: 'var(--text, #eef2f7)' }}><PersonName {...args} /></div>
  ),
};

export const Byline = {
  args: { name: 'Pete Thamel', kind: 'media' },
  render: (args) => (
    <div style={{ fontSize: 13, color: 'var(--text-2, #a4b1c2)' }}>
      ESPN <span style={{ opacity: 0.5 }}>/</span> <PersonName {...args} />
    </div>
  ),
};

export const InASentence = {
  args: { name: 'Marcus Whitfield', kind: 'player' },
  render: (args) => (
    <div style={{ fontSize: 14, color: 'var(--text, #eef2f7)', maxWidth: 360 }}>
      The story of the season has been quarterback <PersonName {...args} />, who has the
      offense humming heading into November.
    </div>
  ),
};

export const LongName = {
  args: { name: 'Antoine Devereaux', kind: 'recruit' },
  render: (args) => (
    <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text, #eef2f7)' }}><PersonName {...args} /></div>
  ),
};
