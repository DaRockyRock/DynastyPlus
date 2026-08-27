import SettingsFab from './SettingsFab.jsx';

export default {
  title: 'Layout/SettingsFab',
  component: SettingsFab,
  parameters: { layout: 'fullscreen' },
};

export const Default = {
  render: () => (
    <div style={{ position: 'relative', height: 200 }}>
      <SettingsFab onClick={() => {}} />
    </div>
  ),
};
