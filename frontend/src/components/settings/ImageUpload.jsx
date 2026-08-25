import { useState, useRef } from 'react';
import { api } from '../../lib/api.js';
import { UploadIcon, TrashIcon, RefreshIcon, ImageIcon } from '../ui/icons.jsx';

// Upload + preview for a single image. Stores the served URL (e.g. /uploads/ab.png)
// as the field value. Click or drop to upload; uploading is delegated to the
// backend which dedupes by content hash. `onUpload` lets the caller swap in its
// own uploader (used by Storybook to avoid network calls).
export default function ImageUpload({ value, onChange, onUpload, hint }) {
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const doUpload = async (file) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const res = onUpload ? await onUpload(file) : await api.uploadImage(file);
      onChange(res.url);
    } catch (e) {
      setError(e.message || 'Upload failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="img-upload">
      <button
        type="button"
        className={`img-drop${drag ? ' drag' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); doUpload(e.dataTransfer.files?.[0]); }}
        aria-label="Upload image"
      >
        {value ? <img src={value} alt="" /> : (busy ? <RefreshIcon /> : <ImageIcon />)}
      </button>
      <div className="iu-meta">
        <div className="iu-hint">{error ? error : (hint || 'PNG, JPG, GIF, WEBP or SVG. Up to 8MB.')}</div>
        <div className="iu-acts">
          <button type="button" className={`iu-btn${busy ? ' spinning' : ''}`} onClick={() => inputRef.current?.click()} disabled={busy}>
            {busy ? <RefreshIcon /> : <UploadIcon />}{value ? 'Replace' : 'Upload'}
          </button>
          {value && (
            <button type="button" className="iu-btn danger" onClick={() => onChange('')} disabled={busy}>
              <TrashIcon />Remove
            </button>
          )}
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={(e) => { doUpload(e.target.files?.[0]); e.target.value = ''; }}
      />
    </div>
  );
}
