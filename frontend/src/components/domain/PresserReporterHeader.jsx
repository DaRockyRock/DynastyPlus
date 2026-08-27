import Avatar from '../ui/Avatar.jsx';
import PersonName from '../people/PersonName.jsx';

// The reporter currently at the podium: avatar, hoverable name, outlet, a
// local/national tag, and a "reporter X of N" progress readout.
export default function PresserReporterHeader({ reporter, index = 0, total = 5 }) {
  if (!reporter) return null;
  const scope = (reporter.scope || 'local') === 'local' ? 'LOCAL' : 'NATIONAL';
  return (
    <div className="presser-reporter">
      <Avatar name={reporter.name} src={reporter.image} size={44} gradient />
      <div className="presser-reporter-id">
        <div className="presser-reporter-name">
          <PersonName name={reporter.name} kind="media" role={reporter.outlet} />
        </div>
        <div className="presser-reporter-sub">
          <span className={`presser-scope ${scope.toLowerCase()}`}>{scope}</span>
          <span className="presser-outlet">{reporter.outlet}</span>
        </div>
      </div>
      <div className="presser-progress">Reporter {index + 1} of {total}</div>
    </div>
  );
}
