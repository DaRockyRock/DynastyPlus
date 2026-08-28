import Toast from './Toast.jsx';

export default {
  title: 'UI/Toast',
  component: Toast,
  parameters: { layout: 'fullscreen' },
};

export const Default = { args: { message: 'Advanced to Week 11' } };
export const ScheduleGenerated = { args: { message: 'Generated a new schedule preview' } };
