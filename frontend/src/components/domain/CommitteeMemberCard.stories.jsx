import CommitteeMemberCard from './CommitteeMemberCard.jsx';
import { committeeMember } from '../fixtures.js';

export default {
  title: 'Domain/CommitteeMemberCard',
  component: CommitteeMemberCard,
  parameters: { layout: 'padded' },
};

export const Chair = {
  render: () => <div style={{ width: 460 }}><CommitteeMemberCard member={committeeMember} onClick={() => {}} /></div>,
};

export const FormerCoach = {
  render: () => (
    <div style={{ width: 460 }}>
      <CommitteeMemberCard
        member={{
          ...committeeMember,
          member: 'Mark Dantonio', role: 'Former HC, Michigan State', affiliation: 'Big Ten',
          conference: 'Big Ten', conference_id: 5, initials: 'MD',
          bio: 'The winningest coach in Michigan State history with three Big Ten titles and a Rose Bowl win.',
          lens: 'A defensive-minded coach who values physical teams that win the line of scrimmage.',
        }}
        onClick={() => {}}
      />
    </div>
  ),
};
