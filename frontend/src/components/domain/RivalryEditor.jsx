import { useState } from 'react';
import PanelCard from '../ui/PanelCard.jsx';
import FormField from '../ui/FormField.jsx';
import Select from '../ui/Select.jsx';
import TextInput from '../ui/TextInput.jsx';
import Button from '../ui/Button.jsx';

// Protected-rivalry editor for one conference. Each row pairs two member teams
// with an optional trophy or game name; the footer adds a new rivalry by
// picking two members and naming it. Rivalries are companion-side flavor (the
// save has no field for them). Presentational: `onChange(rivalries)` hands the
// full updated list back to the page.
export default function RivalryEditor({ conf, onChange }) {
  const teams = conf?.teams || [];
  const rivalries = conf?.rivalries || [];
  const [a, setA] = useState('');
  const [b, setB] = useState('');
  const [name, setName] = useState('');

  const schoolOf = (full) => {
    const entry = teams.includes(full) ? full : null;
    return entry || full;
  };
  const opts = [{ value: '', label: 'Select team' },
    ...teams.map((t) => ({ value: t, label: schoolOf(t) }))];

  const add = () => {
    if (!a || !b || a === b) return;
    onChange?.([...rivalries, { a, b, name: name.trim() }]);
    setA(''); setB(''); setName('');
  };
  const remove = (i) => onChange?.(rivalries.filter((_, idx) => idx !== i));

  return (
    <PanelCard className="cs-riv" flush title="Protected Rivalries">
      {rivalries.length === 0 && (
        <div className="cs-riv-empty">No protected rivalries yet. Add one below.</div>
      )}
      {rivalries.map((r, i) => (
        <div className="cs-riv-row" key={`${r.a}-${r.b}-${i}`}>
          <span className="cs-riv-team"><i>{r.a}</i></span>
          <span className="cs-riv-vs">VS</span>
          <span className="cs-riv-team away"><i>{r.b}</i></span>
          <span className={`cs-riv-name${r.name ? '' : ' none'}`}>{r.name || 'Unnamed rivalry'}</span>
          <Button onClick={() => remove(i)}>Remove</Button>
        </div>
      ))}
      <div className="cs-riv-add">
        <FormField label="Team">
          <Select options={opts} value={a} onValueChange={setA} />
        </FormField>
        <FormField label="Rival">
          <Select options={opts} value={b} onValueChange={setB} />
        </FormField>
        <FormField label="Trophy or Game (optional)">
          <TextInput value={name} maxLength={40} onValueChange={setName} placeholder="Palmetto Bowl" />
        </FormField>
        <Button variant="accent" onClick={add} disabled={!a || !b || a === b}>Add</Button>
      </div>
    </PanelCard>
  );
}
