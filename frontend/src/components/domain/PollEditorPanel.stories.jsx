import PollEditorPanel from './PollEditorPanel.jsx';
import { pollEditorState, pollEntries, pollNativeSealNotice } from '../fixtures.js';

export default {
  title: 'Domain/PollEditorPanel',
  component: PollEditorPanel,
  parameters: { layout: 'fullscreen' },
};

const previewFn = () => Promise.resolve({
  available: true,
  entries: pollEntries.map((e, i) => ({ ...e, delta: (i % 3) - 1 })),
});

export const ManualMode = {
  render: () => (
    <div style={{ padding: 24, maxWidth: 1100 }}>
      <PollEditorPanel initialData={pollEditorState} previewFn={previewFn} userTeam="Nebraska Cornhuskers" />
    </div>
  ),
};

export const ApPollSelected = {
  render: () => (
    <div style={{ padding: 24, maxWidth: 1100 }}>
      <PollEditorPanel
        initialData={pollEditorState}
        initialPoll="ap"
        previewFn={previewFn}
        userTeam="Nebraska Cornhuskers"
      />
    </div>
  ),
};

export const GameOwned = {
  render: () => (
    <div style={{ padding: 24, maxWidth: 1100 }}>
      <PollEditorPanel
        initialData={{
          ...pollEditorState,
          config: { ...pollEditorState.config, polls: { ...pollEditorState.config.polls, cfp: { mode: 'game', algorithm: 'colley', manual: [] } } },
          pending: { cfp: false, ap: false },
        }}
        previewFn={previewFn}
        userTeam="Nebraska Cornhuskers"
      />
    </div>
  ),
};

export const AlgorithmMode = {
  render: () => (
    <div style={{ padding: 24, maxWidth: 1100 }}>
      <PollEditorPanel
        initialData={{
          ...pollEditorState,
          config: { ...pollEditorState.config, polls: { ...pollEditorState.config.polls, cfp: { mode: 'algorithm', algorithm: 'colley', manual: [] } } },
        }}
        previewFn={previewFn}
        userTeam="Nebraska Cornhuskers"
      />
    </div>
  ),
};

export const HeldByPlayoff = {
  render: () => (
    <div style={{ padding: 24, maxWidth: 1100 }}>
      <PollEditorPanel
        initialData={{
          ...pollEditorState,
          holds: { cfp: 'the custom playoff bracket is live; the committee ranking is under playoff control until the season completes', ap: null },
          pending: { cfp: false, ap: false },
        }}
        previewFn={previewFn}
        userTeam="Nebraska Cornhuskers"
      />
    </div>
  ),
};

// The custom playoff is off and the game's own bracket is already seeded
// (bowl season): pushes still write, but the notice explains they can only
// relabel seed numbers, never move teams between bracket slots.
export const NativeBracketAlreadySet = {
  render: () => (
    <div style={{ padding: 24, maxWidth: 1100 }}>
      <PollEditorPanel
        initialData={{
          ...pollEditorState,
          notices: { cfp: pollNativeSealNotice, ap: null },
        }}
        previewFn={previewFn}
        userTeam="Nebraska Cornhuskers"
      />
    </div>
  ),
};

export const NoSave = {
  render: () => (
    <div style={{ padding: 24, maxWidth: 700 }}>
      <PollEditorPanel initialData={{ available: false, reason: 'No CFB 27 save is readable for this dynasty.' }} />
    </div>
  ),
};
