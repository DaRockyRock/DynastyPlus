import Button from '../ui/Button.jsx';

// One save file in the manual-import browser. Shows the program the profile
// knows for the file (or flags that it must be picked by hand), the file name,
// and when it was saved, with an action to bring it into the library. Files
// already in the library are marked and cannot be re-imported.
function prettySave(name) {
  if (!name) return '';
  return name.replace(/^DYNASTY-/i, '').replace(/-AUTOSAVE$/i, ' (autosave)').replace(/-/g, ' ');
}

function prettyDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  });
}

function Chip({ children, tone = 'muted' }) {
  const tones = {
    muted: { color: 'var(--text-2, #9aa6b2)', border: 'var(--border, rgba(255,255,255,0.14))' },
    warn: { color: '#e8b04b', border: 'color-mix(in srgb, #e8b04b 45%, transparent)' },
    ok: { color: '#7bd88f', border: 'color-mix(in srgb, #7bd88f 45%, transparent)' },
  };
  const t = tones[tone] || tones.muted;
  return (
    <span style={{
      font: '700 10.5px "Saira Condensed", sans-serif', letterSpacing: '0.06em',
      textTransform: 'uppercase', color: t.color, padding: '2px 7px', borderRadius: 5,
      border: `1px solid ${t.border}`, whiteSpace: 'nowrap',
    }}>
      {children}
    </span>
  );
}

export default function SaveFileRow({ save, onImport, busy = false }) {
  if (!save) return null;
  const { school, save_name: saveName, saved_at: savedAt, week_label: weekLabel, registered } = save;
  const label = registered ? 'Imported' : (school ? 'Import' : 'Pick team');

  return (
    <div
      style={{
        display: 'flex', alignItems: 'center', gap: 14, padding: '12px 14px',
        borderRadius: 10, background: 'var(--surface-1, #0d1320)',
        border: '1px solid var(--border, rgba(255,255,255,0.08))',
        opacity: registered ? 0.7 : 1,
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0, flex: 1 }}>
        <span style={{
          font: '700 15px "Saira Condensed", sans-serif', letterSpacing: '0.01em',
          textTransform: 'uppercase', color: 'var(--text-1, #e9eef5)',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {school || prettySave(saveName)}
        </span>
        <span style={{
          fontSize: 12, color: 'var(--text-3, #6b7686)',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {school ? `${prettySave(saveName)} • ` : ''}
          {weekLabel ? `${weekLabel} • ` : ''}
          {prettyDate(savedAt)}
        </span>
        <div style={{ display: 'flex', gap: 6, marginTop: 2 }}>
          {registered && <Chip tone="ok">In library</Chip>}
          {!school && !registered && <Chip tone="warn">Team not detected</Chip>}
        </div>
      </div>
      <Button
        variant={registered ? 'action' : 'accent'}
        onClick={() => onImport?.(save)}
        disabled={busy || registered}
        spinning={busy}
      >
        {busy ? 'Importing...' : label}
      </Button>
    </div>
  );
}
