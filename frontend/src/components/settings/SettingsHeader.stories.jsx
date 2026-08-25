import SettingsHeader from './SettingsHeader.jsx';

export default {
  title: 'Settings/SettingsHeader',
  component: SettingsHeader,
  parameters: { layout: 'fullscreen' },
};

export const Default = {
  render: () => <SettingsHeader onClose={() => {}} />,
};
