// Drive-by-drive chart: each possession's team, starting spot, plays, yards,
// time, and result. Reads a game's `drives` list.
const RESULT_CLASS = {
  Touchdown: 'good', 'Field Goal': 'good', Punt: '', Interception: 'bad',
  Fumble: 'bad', Downs: 'bad', 'Missed FG': 'bad', Safety: 'bad',
};

export default function DriveChart({ drives = [] }) {
  if (!drives.length) return <div className="gc-empty">No drive data.</div>;
  return (
    <table className="gc-drives">
      <thead>
        <tr>
          <th>Team</th><th>Qtr</th><th>Start</th><th>Plays</th><th>Yards</th><th>Time</th><th>Result</th>
        </tr>
      </thead>
      <tbody>
        {drives.map((d, i) => (
          <tr key={i}>
            <td className="gc-drive-team">{d.team_abbr}</td>
            <td>{d.quarter === 'OT' ? 'OT' : `${d.quarter}Q`}</td>
            <td>{d.start}</td>
            <td>{d.plays}</td>
            <td>{d.yards}</td>
            <td>{d.time}</td>
            <td><span className={`gc-drive-result ${RESULT_CLASS[d.result] || ''}`}>{d.result}</span></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
