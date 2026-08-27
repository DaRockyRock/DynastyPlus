import RegenerateButton from './RegenerateButton.jsx';

export default {
  title: 'UI/RegenerateButton',
  component: RegenerateButton,
  parameters: { layout: 'centered' },
};

export const Default = { args: { spinning: false } };
export const Spinning = { args: { spinning: true } };
