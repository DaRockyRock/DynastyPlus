import Modal from '../ui/Modal.jsx';
import Avatar from '../ui/Avatar.jsx';
import ConferenceLogo from '../ui/ConferenceLogo.jsx';
import TeamLogo from '../ui/TeamLogo.jsx';
import PersonName from '../people/PersonName.jsx';

// Full top-25 ballot for a committee member, shown when their card is clicked.
export default function CommitteeBallotModal({ member, onClose }) {
  return (
    <Modal open={!!member} onClose={onClose} align="center">
      {member && (
        <div className="ballot-modal modal-card">
          <div className="ballot-modal-head">
            <Avatar label={member.initials} name={member.member} size={46} />
            <div className="bm-meta">
              <div className="bm-name"><PersonName name={member.member} kind="committee" /></div>
              <div className="bm-role">{member.role}</div>
              <div className="bm-conf">
                <ConferenceLogo id={member.conference_id} name={member.conference} size={18} title={member.affiliation} />
                {member.affiliation}
              </div>
            </div>
            <button className="bm-close" onClick={onClose} aria-label="Close">&times;</button>
          </div>
          <div className="bm-subhead">Full Top 25 Ballot</div>
          <div className="ballot-modal-body">
            {(member.top25 || []).map((t) => (
              <div className={`ballot-row${t.rank <= 4 ? ' is-top4' : ''}`} key={t.rank}>
                <span className="br-rank">{t.rank}</span>
                <TeamLogo espnId={t.espn_id} abbr={t.abbr} name={t.team} size={26} />
                <span className="br-team">{t.team}</span>
                <span className="br-rec">{t.record}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Modal>
  );
}
