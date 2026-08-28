import TaleOfTheTape from './TaleOfTheTape.jsx';
import { teamResume, teamResumeB } from '../fixtures.js';

export default {
  title: 'Domain/TaleOfTheTape',
  component: TaleOfTheTape,
};

export const PlayoffEdgeCase = { args: { a: teamResume, b: teamResumeB } };
