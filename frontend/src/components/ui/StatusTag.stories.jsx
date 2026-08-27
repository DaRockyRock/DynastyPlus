import StatusTag from './StatusTag.jsx';

export default {
  title: 'UI/StatusTag',
  component: StatusTag,
  parameters: { layout: 'centered' },
  argTypes: { status: { control: 'select', options: ['developing', 'corroborated', 'disputed'] } },
};

export const Developing = { args: { status: 'developing' } };
export const Corroborated = { args: { status: 'corroborated' } };
export const Disputed = { args: { status: 'disputed' } };
