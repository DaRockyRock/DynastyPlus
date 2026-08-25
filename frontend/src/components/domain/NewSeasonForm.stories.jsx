import NewSeasonForm from './NewSeasonForm.jsx';

export default {
  title: 'Domain/NewSeasonForm',
  component: NewSeasonForm,
  parameters: { layout: 'padded' },
};

export const Default = { render: () => <div style={{ width: 460 }}><NewSeasonForm defaultYear={2027} onStart={(y, s) => alert(`start ${y} seed ${s}`)} /></div> };

export const Busy = { render: () => <div style={{ width: 460 }}><NewSeasonForm defaultYear={2027} busy /></div> };
