import AwardBlock from './AwardBlock.jsx';
import { award } from '../fixtures.js';

export default {
  title: 'Domain/AwardBlock',
  component: AwardBlock,
  parameters: { layout: 'padded' },
};

export const Heisman = { render: () => <div style={{ width: 520 }}><AwardBlock award={award} /></div> };
export const NoNotes = {
  render: () => <div style={{ width: 520 }}><AwardBlock award={{ ...award, name: 'Biletnikoff Award', criteria: 'Best receiver', notes: [] }} /></div>,
};
