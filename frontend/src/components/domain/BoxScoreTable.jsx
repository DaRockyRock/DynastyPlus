import PersonName from '../people/PersonName.jsx';

// Per-player box score for ONE team: passing, rushing, receiving, and defense
// tables. Names are hoverable (PersonName) so the coach can text a player. Reads
// one side of a game's `box` block.
const GROUPS = [
  { key: 'passing', title: 'Passing', cols: [['c_att', 'C/ATT'], ['yards', 'YDS'], ['td', 'TD'], ['int', 'INT']] },
  { key: 'rushing', title: 'Rushing', cols: [['car', 'CAR'], ['yards', 'YDS'], ['td', 'TD'], ['long', 'LNG']] },
  { key: 'receiving', title: 'Receiving', cols: [['rec', 'REC'], ['yards', 'YDS'], ['td', 'TD'], ['long', 'LNG']] },
  { key: 'defense', title: 'Defense', cols: [['tackles', 'TKL'], ['sacks', 'SACK'], ['tfl', 'TFL'], ['int', 'INT'], ['pd', 'PD']] },
];

export default function BoxScoreTable({ box, isUser = false }) {
  if (!box) return null;
  return (
    <div className="gc-box">
      {GROUPS.map((g) => {
        const rows = box[g.key] || [];
        if (!rows.length) return null;
        return (
          <div className="gc-box-group" key={g.key}>
            <div className="gc-box-title">{g.title}</div>
            <table className="gc-box-table">
              <thead>
                <tr>
                  <th className="gc-box-name">Player</th>
                  {g.cols.map(([, label]) => <th key={label}>{label}</th>)}
                </tr>
              </thead>
              <tbody>
                {rows.map((p, i) => (
                  <tr key={i}>
                    <td className="gc-box-name">
                      {isUser ? <PersonName name={p.name} kind="player" /> : p.name}
                    </td>
                    {g.cols.map(([k, label]) => <td key={label}>{p[k]}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}
