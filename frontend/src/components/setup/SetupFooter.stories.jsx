import SetupFooter from './SetupFooter.jsx';

export default {
  title: 'Setup/SetupFooter',
  component: SetupFooter,
  parameters: { layout: 'fullscreen' },
};

export const Continue = {
  args: { onPrimary: () => {}, primaryLabel: 'Continue' },
};

export const WithHint = {
  args: {
    onBack: () => {},
    onPrimary: () => {},
    hint: 'Game folder detected',
  },
};
