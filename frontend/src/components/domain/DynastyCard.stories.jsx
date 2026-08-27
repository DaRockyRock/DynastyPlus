import DynastyCard from './DynastyCard.jsx';

export default {
  title: 'Domain/DynastyCard',
  component: DynastyCard,
  parameters: { layout: 'padded' },
};

const dynasty = {
  id: 'nebraska', team_name: 'Nebraska Cornhuskers', school: 'Nebraska', abbreviation: 'NEB',
  espn_id: 158, color: 'e41c38', alt_color: 'f5f5f5', logo: '', conference: 'Big Ten',
  year: 2026, week: 8, week_label: 'Week 8', record: '6-1', head_coach: 'Garrett Mason',
};

export const Default = { render: () => <div style={{ width: 560 }}><DynastyCard dynasty={dynasty} onContinue={() => {}} /></div> };
export const Preseason = {
  render: () => <div style={{ width: 560 }}><DynastyCard dynasty={{ ...dynasty, week: 0, week_label: 'Preseason', record: '0-0' }} onContinue={() => {}} /></div>,
};
