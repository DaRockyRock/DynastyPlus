import React from 'react';
import { createRoot } from 'react-dom/client';
import SimulatorApp from './SimulatorApp.jsx';

// In dev, route this app's /api calls to the Simulator backend (5070) via the
// Vite proxy. In production it is served by the Simulator's own Flask, so a
// relative /api already resolves there.
if (import.meta.env && import.meta.env.DEV) {
  window.__API_BASE__ = '/sim-api';
}

// Same athletic broadcast type system + tokens as the companion (shared library).
import '@fontsource/saira/400.css';
import '@fontsource/saira/500.css';
import '@fontsource/saira/600.css';
import '@fontsource/saira/700.css';
import '@fontsource/saira-condensed/600.css';
import '@fontsource/saira-condensed/700.css';
import '@fontsource/saira-condensed/800.css';

import './styles/tokens.css';
import './styles/global.css';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <SimulatorApp />
  </React.StrictMode>
);
