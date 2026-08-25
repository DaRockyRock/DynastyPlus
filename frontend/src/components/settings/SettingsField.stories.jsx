import { useState } from 'react';
import SettingsField from './SettingsField.jsx';

export default {
  title: 'Settings/SettingsField',
  component: SettingsField,
  parameters: { layout: 'padded' },
};

const mockUpload = (file) =>
  new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve({ url: reader.result });
    reader.readAsDataURL(file);
  });

function One({ field, initial }) {
  const [v, setV] = useState(initial);
  return (
    <div className="set-grid" style={{ maxWidth: 560 }}>
      <SettingsField field={field} value={v} onChange={setV} onUpload={mockUpload} />
    </div>
  );
}

export const Text = { render: () => <One field={{ key: 'name', label: 'Name', type: 'text', width: 'full' }} initial="Garrett Mason" /> };
export const TextArea = { render: () => <One field={{ key: 'bio', label: 'Biography', type: 'textarea', width: 'full', help: 'A short factual bio.' }} initial="Third-year head coach who rebuilt the culture." /> };
export const Select = { render: () => <One field={{ key: 'trend', label: 'Trend', type: 'select', width: 'full', options: [{ value: 'up', label: 'Up' }, { value: 'flat', label: 'Flat' }, { value: 'down', label: 'Down' }] }} initial="up" /> };
export const Money = { render: () => <One field={{ key: 'nil', label: 'Expected NIL', type: 'money', width: 'full' }} initial={450000} /> };
export const Percent = { render: () => <One field={{ key: 'heat', label: 'Hot seat', type: 'percent', width: 'full' }} initial={62} /> };
export const Stars = { render: () => <One field={{ key: 'stars', label: 'Stars', type: 'stars', width: 'full' }} initial={4} /> };
export const Color = { render: () => <One field={{ key: 'color', label: 'Primary color', type: 'color', width: 'full' }} initial="e41c38" /> };
export const Image = { render: () => <One field={{ key: 'image', label: 'Photo', type: 'image', width: 'full' }} initial="" /> };
