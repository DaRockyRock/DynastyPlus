import { useEffect } from 'react';

// Generic overlay. `align` controls placement ('center' | 'right'). Closes on
// backdrop click and Escape.
export default function Modal({ open, onClose, align = 'center', className = '', children }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  return (
    <div
      className={['modal-overlay', align, open ? 'open' : '', className].filter(Boolean).join(' ')}
      onClick={(e) => { if (e.target === e.currentTarget) onClose?.(); }}
    >
      {children}
    </div>
  );
}
