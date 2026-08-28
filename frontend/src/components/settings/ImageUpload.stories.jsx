import { useState } from 'react';
import ImageUpload from './ImageUpload.jsx';

export default {
  title: 'Settings/ImageUpload',
  component: ImageUpload,
  parameters: { layout: 'padded' },
};

// Mock uploader: turns the picked file into a local data URL so the story works
// without the backend.
const mockUpload = (file) =>
  new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve({ url: reader.result });
    reader.readAsDataURL(file);
  });

export const Empty = {
  render: () => {
    const [v, setV] = useState('');
    return <div style={{ maxWidth: 420 }}><ImageUpload value={v} onChange={setV} onUpload={mockUpload} /></div>;
  },
};

export const WithImage = {
  render: () => {
    const [v, setV] = useState('https://a.espncdn.com/i/teamlogos/ncaa/500/158.png');
    return <div style={{ maxWidth: 420 }}><ImageUpload value={v} onChange={setV} onUpload={mockUpload} /></div>;
  },
};
