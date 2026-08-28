import PanelCard from '../ui/PanelCard.jsx';
import Button from '../ui/Button.jsx';
import TeamLogo from '../ui/TeamLogo.jsx';

// The membership board for one conference: every member team as a flush game
// row (logo, school, nickname, abbr) with a Move affordance that opens the
// TeamMovePicker. The header shows the count against the save's membership
// limits ("17 of 20 teams") and flips to a warning state when the conference
// is under its minimum or at capacity. `teamsByName` maps full team names to
// the directory entries from the setup state.
export default function ConferenceMemberList({ conf, teamsByName = {}, onMove }) {
  if (!conf) return null;
  const teams = conf.teams || [];
  const limits = conf.limits;
  const underMin = !!limits && teams.length < limits.min;
  const atMax = !!limits && teams.length >= limits.max;
  const count = limits
    ? `${teams.length} of ${limits.max} teams${underMin ? `, under minimum of ${limits.min}` : atMax ? ', at capacity' : ''}`
    : `${teams.length} team${teams.length === 1 ? '' : 's'}`;

  return (
    <PanelCard
      className="cs-members"
      flush
      title="Members"
      right={<span className={`cs-count${underMin || atMax ? ' warn' : ''}`}>{count}</span>}
    >
      {teams.length === 0 && (
        <div className="cs-member-empty">
          No member teams yet. Move teams here from another conference.
        </div>
      )}
      <div className="cs-member-scroll">
        {teams.map((name) => {
          const entry = teamsByName[name];
          const school = entry?.school || name;
          const nickname = entry && name.startsWith(entry.school)
            ? name.slice(entry.school.length).trim()
            : '';
          return (
            <div className="cs-member-row" key={name}>
              <TeamLogo espnId={entry?.espn_id} name={name} abbr={entry?.abbreviation} logo={entry?.logo || ''} size={30} />
              <span className="cs-member-id">
                <span className="cs-member-school">{school}</span>
                {nickname && <span className="cs-member-nick">{nickname}</span>}
              </span>
              {entry?.abbreviation && <span className="cs-member-abbr">{entry.abbreviation}</span>}
              {onMove && <Button onClick={() => onMove(name)}>Move</Button>}
            </div>
          );
        })}
      </div>
    </PanelCard>
  );
}
