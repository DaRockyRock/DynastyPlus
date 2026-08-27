import SourcePill from './SourcePill.jsx';

export default {
  title: 'UI/SourcePill',
  component: SourcePill,
  parameters: { layout: 'centered' },
  argTypes: { source: { control: 'select', options: ['mock', 'static'] } },
};

export const Mock = { args: { source: 'mock' } };
export const Static = { args: { source: 'static' } };
