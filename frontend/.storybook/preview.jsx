import '@fontsource/saira/400.css';
import '@fontsource/saira/500.css';
import '@fontsource/saira/600.css';
import '@fontsource/saira/700.css';
import '@fontsource/saira-condensed/600.css';
import '@fontsource/saira-condensed/700.css';
import '@fontsource/saira-condensed/800.css';

import '../src/styles/tokens.css';
import '../src/styles/global.css';
import '../src/styles/screens-recruiting.css';
import '../src/styles/screens-league.css';
import '../src/styles/screens-conferences.css';
import '../src/styles/screens-setup.css';
import '../src/styles/screens-polls.css';
import '../src/styles/screens-schedule.css';
import '../src/styles/screens-bowls.css';

/** @type { import('@storybook/react-vite').Preview } */
const preview = {
  parameters: {
    layout: 'centered',
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    backgrounds: {
      options: { dark: { name: 'dark', value: '#0a0e14' } },
    },
    a11y: {
      test: 'todo',
    },
  },
  initialGlobals: {
    backgrounds: { value: 'dark' },
  },
  decorators: [
    (Story) => (
      <div style={{ color: 'var(--text)', fontFamily: 'var(--font)', width: '100%' }}>
        <Story />
      </div>
    ),
  ],
};

export default preview;
