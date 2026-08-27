import Stepper from './Stepper.jsx';

const STEPS = ['Welcome', 'Connect', 'Confirm'];

export default {
  title: 'UI/Stepper',
  component: Stepper,
  parameters: { layout: 'padded' },
};

export const Start = { args: { steps: STEPS, current: 0 } };
export const Middle = { args: { steps: STEPS, current: 1 } };
export const End = { args: { steps: STEPS, current: 2 } };
