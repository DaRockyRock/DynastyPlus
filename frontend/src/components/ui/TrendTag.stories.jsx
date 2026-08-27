import TrendTag from './TrendTag.jsx';

export default {
  title: 'UI/TrendTag',
  component: TrendTag,
  parameters: { layout: 'centered' },
  argTypes: { trend: { control: 'select', options: ['up', 'flat', 'down'] } },
};

export const Up = { args: { trend: 'up' } };
export const Flat = { args: { trend: 'flat' } };
export const Down = { args: { trend: 'down' } };
