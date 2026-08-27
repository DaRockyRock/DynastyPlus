import LoadingOverlay from './LoadingOverlay.jsx';

const team = { name: 'Nebraska Cornhuskers', abbreviation: 'NEB', espn_id: 158, color: 'e41c38' };

export default {
  title: 'Layout/LoadingOverlay',
  component: LoadingOverlay,
  parameters: { layout: 'fullscreen' },
};

export const MidGeneration = {
  args: { active: true, week: 11, team, progress: 4, total: 9, module: 'cfp_committee', subStep: 'Marcus Freeman' },
};

export const InboundTexts = {
  args: { active: true, week: 11, team, progress: 9, total: 12, module: 'inbound', subStep: 'Jordan Davis' },
};

export const NoSubStep = {
  args: { active: true, week: 3, team, progress: 1, total: 12, module: 'top_stories', subStep: '5 headline stories' },
};

// After a game completes: the press conference is starting (no module progress yet).
export const PresserOpening = {
  args: { active: true, week: 11, team, title: 'Post-game', caption: 'Heading to the press conference' },
};

// After the presser, the held post-game coverage regenerates with the coach's answers.
export const PostGameCoverage = {
  args: { active: true, week: 11, team, progress: 1, total: 3, module: 'news_feed', subStep: 'Reaction to the win', title: 'Post-game coverage', caption: 'Writing the week’s headlines' },
};
