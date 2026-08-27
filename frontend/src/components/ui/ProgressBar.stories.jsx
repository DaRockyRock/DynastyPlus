import ProgressBar from './ProgressBar.jsx';

export default {
  title: 'UI/ProgressBar',
  component: ProgressBar,
  parameters: { layout: 'padded' },
  argTypes: { value: { control: { type: 'range', min: 0, max: 100 } } },
};

export const Quarter = { args: { value: 25 } };
export const Half = { args: { value: 50 } };
export const Full = { args: { value: 100 } };
