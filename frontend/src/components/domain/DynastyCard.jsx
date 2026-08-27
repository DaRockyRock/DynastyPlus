import TeamLogo from '../ui/TeamLogo.jsx';
import Button from '../ui/Button.jsx';
import { hexColor } from '../../lib/format.js';

// A scanned dynasty in the library landing screen: team mark + record + the week
// it was last scanned at, with a Continue action. Selecting it enters the app.
export default function DynastyCard({ dynasty, onContinue, busy = false }) {
  if (!dynasty) return null;
  const accent = hexColor(dynasty.color, '#e41c38');
  return (
    <div
      className="dynasty-card"
      style={{
        display: 'flex', alignItems: 'center', gap: 16, padding: '16px 18px',
        borderRadius: 12, background: 'var(--surface-1, #0d1320)',
        border: '1px solid var(--border, rgba(255,255,255,0.08))',
        borderLeft: `4px solid ${accent}`,
      }}
    >
      <TeamLogo espnId={dynasty.espn_id} logo={dynasty.logo} abbr={dynasty.abbreviation}
                name={dynasty.team_name} color={accent} size={54} plate={false} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0, flex: 1 }}>
        <span style={{
          font: '700 19px "Saira Condensed", sans-serif', letterSpacing: '0.01em',
          textTransform: 'uppercase', color: 'var(--text-1, #e9eef5)',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {dynasty.team_name}
        </span>
        <span style={{ fontSize: 13, color: 'var(--text-2, #9aa6b2)' }}>
          {dynasty.year} season • {dynasty.week_label || `Week ${dynasty.week}`}
          {dynasty.record ? ` • ${dynasty.record}` : ''}
        </span>
        {dynasty.head_coach && (
          <span style={{ fontSize: 12, color: 'var(--text-3, #6b7686)' }}>{dynasty.head_coach}</span>
        )}
      </div>
      <Button variant="accent" onClick={() => onContinue?.(dynasty.id)} disabled={busy}>
        Continue
      </Button>
    </div>
  );
}
