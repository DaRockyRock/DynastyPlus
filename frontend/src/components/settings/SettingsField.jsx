import ColorField from './ColorField.jsx';
import StarField from './StarField.jsx';
import TeamField from './TeamField.jsx';
import ImageUpload from './ImageUpload.jsx';
import PersonalitySliders from './PersonalitySliders.jsx';

// Common conferences offered as autocomplete for conference fields.
const CONFERENCES = [
  'Big Ten', 'SEC', 'ACC', 'Big 12', 'Pac-12', 'American', 'Mountain West',
  'Conference USA', 'MAC', 'Sun Belt', 'Independent',
];

// Renders one editable field by its schema `type`, wrapped with a label, the
// width-span class, and optional help text. `value`/`onChange` are the value of
// this single field (the parent resolves dot paths).
export default function SettingsField({ field, value, onChange, onUpload }) {
  const { type, label, width = 'full', help, placeholder, options = [], min, max, step, maxLength } = field;
  const widthClass = `w-${width}`;

  const num = (raw, asFloat) => {
    if (raw === '' || raw == null) return '';
    return asFloat ? parseFloat(raw) : parseInt(raw, 10);
  };

  let control;
  switch (type) {
    case 'textarea':
      control = (
        <textarea className="set-textarea" value={value ?? ''} placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)} />
      );
      break;
    case 'select':
      control = (
        <select className="set-select" value={value ?? ''} onChange={(e) => onChange(e.target.value)}>
          {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      );
      break;
    case 'color':
      control = <ColorField value={value} onChange={onChange} />;
      break;
    case 'stars':
      control = <StarField value={value} onChange={onChange} />;
      break;
    case 'team':
      control = <TeamField value={value} onChange={onChange} placeholder={placeholder} />;
      break;
    case 'image':
      control = <ImageUpload value={value} onChange={onChange} hint={help} onUpload={onUpload} />;
      break;
    case 'personality':
      control = <PersonalitySliders value={value || {}} onChange={onChange} />;
      break;
    case 'money':
      control = (
        <div className="set-input-affix has-pre">
          <span className="pre">$</span>
          <input className="set-input" type="number" inputMode="numeric" value={value ?? ''} min={0}
            placeholder={placeholder} onChange={(e) => onChange(num(e.target.value))} />
        </div>
      );
      break;
    case 'percent':
      control = (
        <input className="set-input" type="number" value={value ?? ''} min={min ?? 0} max={max ?? 100}
          onChange={(e) => onChange(num(e.target.value))} />
      );
      break;
    case 'rating':
      control = (
        <input className="set-input" type="number" value={value ?? ''} min={min ?? 0} max={max ?? 1}
          step={step ?? 0.0001} placeholder={placeholder} onChange={(e) => onChange(num(e.target.value, true))} />
      );
      break;
    case 'number':
    case 'year':
      control = (
        <input className="set-input" type="number" value={value ?? ''} min={min} max={max} step={step}
          placeholder={placeholder} onChange={(e) => onChange(num(e.target.value))} />
      );
      break;
    case 'slug':
      control = (
        <input className="set-input" value={value ?? ''} placeholder={placeholder} maxLength={maxLength}
          onChange={(e) => onChange(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))} />
      );
      break;
    case 'team_conference':
      control = (
        <>
          <input className="set-input" list="cfbmod-conferences" value={value ?? ''} placeholder={placeholder}
            onChange={(e) => onChange(e.target.value)} />
          <datalist id="cfbmod-conferences">
            {CONFERENCES.map((c) => <option key={c} value={c} />)}
          </datalist>
        </>
      );
      break;
    default:
      control = (
        <input className="set-input" value={value ?? ''} placeholder={placeholder} maxLength={maxLength}
          onChange={(e) => onChange(e.target.value)} />
      );
  }

  return (
    <label className={`set-field ${widthClass}`}>
      <span className="set-label">{label}</span>
      {control}
      {help && type !== 'image' && <span className="set-help">{help}</span>}
    </label>
  );
}
