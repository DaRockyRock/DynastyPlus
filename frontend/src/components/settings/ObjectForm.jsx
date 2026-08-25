import FieldGrid from './FieldGrid.jsx';

// Editor for an object section (Team Identity, Head Coach, Program Blueprint).
// Thin wrapper around FieldGrid; kept as its own component so object sections
// and list-item bodies stay visually consistent and independently storyable.
export default function ObjectForm({ section, value, onChange, onUpload }) {
  return <FieldGrid fields={section.fields} value={value || {}} onChange={onChange} onUpload={onUpload} />;
}
