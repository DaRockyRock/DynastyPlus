import Card from '../ui/Card.jsx';
import Avatar from '../ui/Avatar.jsx';
import ConferenceLogo from '../ui/ConferenceLogo.jsx';
import PersonName from '../people/PersonName.jsx';
import { noEmDash } from '../../lib/format.js';

// A CFP committee member: avatar, name, role, conference affiliation logo, a
// short biography, the simulated "lens", and the top of their ballot. Clicking
// opens the full top-25 ballot.
export default function CommitteeMemberCard({ member, onClick }) {
  const m = member;
  const top4 = (m.top25 || m.top12 || []).slice(0, 4);
  const label = (t) => (typeof t === 'string' ? t : (t.abbr || t.team));

  return (
    <Card className="member-card" onClick={onClick}>
      <div className="m-head">
        <Avatar label={m.initials} name={m.member} size={42} src={m.photo} />
        <div>
          <div className="m-name"><PersonName name={m.member} kind="committee" /></div>
          <div className="m-role">{m.role}</div>
        </div>
        <span className="m-affil">
          <ConferenceLogo id={m.conference_id} name={m.conference} size={22} title={m.affiliation} />
          <span className="affiliation-tag">{m.affiliation}</span>
        </span>
      </div>
      <div className="m-bias">&quot;{noEmDash(m.lens || m.bias)}&quot;</div>
      <div className="m-bio">{noEmDash(m.bio)}</div>
      <div className="ballot">
        {top4.map((t, i) => <span className="b-item" key={i}><b>{i + 1}</b> {label(t)}</span>)}
        {m.lower_on && <span className="b-item" style={{ color: 'var(--loss)' }}>Lower on: {m.lower_on}</span>}
      </div>
      <div className="m-view">View full top 25 &rarr;</div>
    </Card>
  );
}
