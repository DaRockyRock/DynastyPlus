import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';

// Athletic broadcast type system: Saira (body) + Saira Condensed (display).
import '@fontsource/saira/400.css';
import '@fontsource/saira/500.css';
import '@fontsource/saira/600.css';
import '@fontsource/saira/700.css';
import '@fontsource/saira-condensed/600.css';
import '@fontsource/saira-condensed/700.css';
import '@fontsource/saira-condensed/800.css';

import './styles/tokens.css';
import './styles/global.css';
import './styles/screens-recruiting.css';
import './styles/screens-league.css';
import './styles/screens-conferences.css';
import './styles/screens-setup.css';
import './styles/screens-polls.css';
import './styles/screens-schedule.css';
import './styles/screens-bowls.css';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
