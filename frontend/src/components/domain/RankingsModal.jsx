import { useState } from 'react';
import Modal from '../ui/Modal.jsx';
import SegmentedControl from '../ui/SegmentedControl.jsx';
import RankingList from './RankingList.jsx';
import ReceivingVotes from './ReceivingVotes.jsx';

const POLLS = [
  { value: 'cfp', label: 'CFP', title: 'College Football Playoff' },
  { value: 'ap', label: 'AP Poll', title: 'Associated Press Top 25' },
  { value: 'coaches', label: 'Coaches', title: 'Coaches Poll Top 25' },
];

// Full rankings overlay. Toggles between the CFP field, AP poll, and Coaches
// poll; the two media polls include a Receiving Votes section.
export default function RankingsModal({ open, national, userTeam, initialPoll = 'cfp', onClose }) {
  const [poll, setPoll] = useState(initialPoll);
  const n = national || {};

  const views = {
    cfp: { teams: n.cfp_top12 || [], receiving: null },
    ap: { teams: n.ap_top25 || [], receiving: n.ap_receiving_votes },
    coaches: { teams: n.coaches_top25 || [], receiving: n.coaches_receiving_votes },
  };
  const view = views[poll] || views.cfp;
  const meta = POLLS.find((p) => p.value === poll);

  return (
    <Modal open={open} onClose={onClose} align="center">
      {open && (
        <div className="rankings-modal modal-card">
          <div className="rankings-head">
            <div>
              <div className="rm-title">Rankings</div>
              <div className="rm-sub">{meta.title}</div>
            </div>
            <button className="bm-close" onClick={onClose} aria-label="Close">&times;</button>
          </div>
          <div className="rankings-tabs">
            <SegmentedControl
              options={POLLS.map((p) => ({ value: p.value, label: p.label }))}
              value={poll}
              onChange={setPoll}
            />
          </div>
          <div className="rankings-body">
            <RankingList teams={view.teams} userTeam={userTeam} />
            {view.receiving && <ReceivingVotes teams={view.receiving} />}
          </div>
        </div>
      )}
    </Modal>
  );
}
