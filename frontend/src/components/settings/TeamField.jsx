import { useState, useEffect } from 'react';
import TeamLogo from '../ui/TeamLogo.jsx';
import { api } from '../../lib/api.js';

// Team name editor: a text input backed by a datalist of real schools, with a
// live logo preview. The teams index is fetched once and shared across every
// TeamField instance; if the fetch fails (e.g. Storybook) it degrades to a
// plain text input with a monogram preview.
let _teamsPromise = null;
function loadTeams() {
  if (!_teamsPromise) {
    _teamsPromise = api.teams().catch(() => ({}));
  }
  return _teamsPromise;
}

export default function TeamField({ value, onChange, placeholder = 'Team name' }) {
  const [index, setIndex] = useState({});
  useEffect(() => {
    let alive = true;
    loadTeams().then((data) => { if (alive) setIndex(data || {}); });
    return () => { alive = false; };
  }, []);

  const match = index[value] || null;
  const names = Object.keys(index);

  return (
    <div className="team-field">
      <span className="tf-logo">
        <TeamLogo espnId={match?.espn_id} name={value} abbr={match?.abbreviation} color={match?.color} size={36} />
      </span>
      <input
        className="set-input"
        list="cfbmod-teams"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
      {names.length > 0 && (
        <datalist id="cfbmod-teams">
          {names.map((n) => <option key={n} value={n} />)}
        </datalist>
      )}
    </div>
  );
}
