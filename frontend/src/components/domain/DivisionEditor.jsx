import PanelCard from '../ui/PanelCard.jsx';
import TextInput from '../ui/TextInput.jsx';
import TeamLogo from '../ui/TeamLogo.jsx';

// Division board for a conference that has two or more divisions (the Sun Belt
// splits East / West). One column per division: an editable division name and
// the member teams, each with a swap control that moves the team to the next
// division in the ring. Presentational: `onRename(row, name)` and
// `onSwap(teamName)` are owned by the page. `teamsByName` maps full names to
// directory entries for the logos.
export default function DivisionEditor({ conf, teamsByName = {}, onRename, onSwap }) {
  const divisions = conf?.divisions || [];
  if (divisions.length < 2) return null;
  const nextName = (i) => divisions[(i + 1) % divisions.length].name;

  return (
    <PanelCard className="cs-div" title="Divisions">
      <div className="cs-div-grid">
        {divisions.map((div, i) => (
          <div className="cs-div-col" key={div.row ?? div.name}>
            <TextInput
              value={div.name || ''}
              maxLength={20}
              onValueChange={(v) => onRename?.(div.row, v)}
            />
            <div className="cs-div-teams">
              {(div.teams || []).length === 0 && (
                <div className="cs-div-empty">No teams in this division.</div>
              )}
              {(div.teams || []).map((name) => {
                const entry = teamsByName[name];
                return (
                  <div className="cs-div-team" key={name}>
                    <TeamLogo espnId={entry?.espn_id} name={name} abbr={entry?.abbreviation} logo={entry?.logo || ''} size={26} />
                    <span className="cs-div-team-name">{entry?.school || name}</span>
                    {onSwap && (
                      <button className="cs-div-swap" onClick={() => onSwap(name)}>
                        To {nextName(i)}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </PanelCard>
  );
}
