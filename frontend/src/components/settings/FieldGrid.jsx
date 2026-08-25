import SettingsField from './SettingsField.jsx';
import { getPath, setPath } from '../../lib/objectPath.js';

// Lays out a record's fields in the responsive settings grid and wires each
// field to its (possibly nested) key on the record. `value` is the record,
// `onChange` receives the updated record.
export default function FieldGrid({ fields, value, onChange, onUpload }) {
  return (
    <div className="set-grid">
      {fields.map((field) => (
        <SettingsField
          key={field.key}
          field={field}
          value={getPath(value, field.key)}
          onChange={(v) => onChange(setPath(value, field.key, v))}
          onUpload={onUpload}
        />
      ))}
    </div>
  );
}
