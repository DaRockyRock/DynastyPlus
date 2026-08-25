import HeatBar from './HeatBar.jsx';

export default {
  title: 'UI/HeatBar',
  component: HeatBar,
  parameters: { layout: 'centered' },
  argTypes: { value: { control: { type: 'range', min: 0, max: 100 } } },
};

export const Cool = { args: { value: 12 } };
export const Warm = { args: { value: 62 } };
export const Hot = { args: { value: 88 } };
