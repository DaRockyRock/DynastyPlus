import TeamResumeModal from './TeamResumeModal.jsx';
import { pollEntries, teamResume, teamResumeB } from '../fixtures.js';

export default {
  title: 'Domain/TeamResumeModal',
  component: TeamResumeModal,
};

const loadResume = async (row) => (row === 5 ? teamResumeB : teamResume);

export const Resume = {
  args: {
    open: true,
    resume: teamResume,
    entries: pollEntries,
    loadResume,
    onClose: () => {},
  },
};

export const ComparisonOpen = {
  args: {
    open: true,
    resume: teamResume,
    entries: pollEntries,
    loadResume,
    initialCompareRow: 5,
    onClose: () => {},
  },
};

export const Loading = {
  args: { open: true, resume: null, loading: true, entries: pollEntries, loadResume, onClose: () => {} },
};
