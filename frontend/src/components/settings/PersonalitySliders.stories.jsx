import { useState } from 'react';
import PersonalitySliders from './PersonalitySliders.jsx';

export default {
  title: 'Settings/PersonalitySliders',
  component: PersonalitySliders,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => {
    const [v, setV] = useState({
      confidence: 80, competitiveness: 92, loyalty: 55, composure: 78,
      charisma: 60, ambition: 88, ego: 58,
    });
    return <div style={{ maxWidth: 640 }}><PersonalitySliders value={v} onChange={setV} /></div>;
  },
};

export const FreshDraw = {
  render: () => {
    const [v, setV] = useState({});
    return <div style={{ maxWidth: 640 }}><PersonalitySliders value={v} onChange={setV} /></div>;
  },
};
