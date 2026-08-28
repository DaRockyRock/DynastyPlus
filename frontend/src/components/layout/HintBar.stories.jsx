import HintBar from './HintBar.jsx';

export default {
  title: 'Layout/HintBar',
  component: HintBar,
  parameters: { layout: 'fullscreen' },
};

export const Default = {
  args: {
    hints: [
      { key: 'S', label: 'Scan Save', onClick: () => {} },
      { key: 'ENTER', label: 'Apply', onClick: () => {} },
      { key: 'ESC', label: 'Back', dark: true },
    ],
  },
  render: (args) => (
    <div style={{ minHeight: 120, position: 'relative' }}>
      <HintBar {...args} />
    </div>
  ),
};

export const PassiveOnly = {
  args: {
    hints: [
      { key: 'ENTER', label: 'Select', dark: true },
      { key: 'ESC', label: 'Back', dark: true },
    ],
    brand: 'DYNASTY+ TOOLS | WEEK 3, 2026',
  },
  render: (args) => (
    <div style={{ minHeight: 120, position: 'relative' }}>
      <HintBar {...args} />
    </div>
  ),
};
