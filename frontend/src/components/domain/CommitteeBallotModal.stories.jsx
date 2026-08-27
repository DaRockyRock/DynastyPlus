import { useState } from 'react';
import CommitteeBallotModal from './CommitteeBallotModal.jsx';
import Button from '../ui/Button.jsx';
import { committeeMember } from '../fixtures.js';

export default {
  title: 'Domain/CommitteeBallotModal',
  component: CommitteeBallotModal,
  parameters: { layout: 'fullscreen' },
};

export const Open = {
  render: () => {
    function Demo() {
      const [member, setMember] = useState(committeeMember);
      return (
        <div style={{ padding: 40 }}>
          <Button variant="accent" onClick={() => setMember(committeeMember)}>Open ballot</Button>
          <CommitteeBallotModal member={member} onClose={() => setMember(null)} />
        </div>
      );
    }
    return <Demo />;
  },
};
