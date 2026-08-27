import SourcePill from './SourcePill.jsx';

export default {
  title: 'UI/SourcePill',
  component: SourcePill,
  parameters: { layout: 'centered' },
  argTypes: { source: { control: 'select', options: ['mock', 'llm', 'static'] } },
};

export const Mock = { args: { source: 'mock' } };
export const Llm = { args: { source: 'llm' } };
export const Static = { args: { source: 'static' } };
