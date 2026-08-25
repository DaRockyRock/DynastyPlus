import TeamLogo from '../ui/TeamLogo.jsx';
import { hexColor } from '../../lib/format.js';

export default function ToolsTopBar({ team = {}, sim }) {
  const active = !!sim?.active;
  return (
    <header className="sim-topbar" style={{
      display: 'flex', alignItems: 'center', gap: 16, padding: '12px 20px',
      borderBottom: '1px solid var(--border, rgba(255,255,255,0.08))',
      background: 'var(--surface-1, #0d1320)',
    }}>
      <span style={{
        font: '800 13px "Saira Condensed", sans-serif', letterSpacing: '0.18em',
        textTransform: 'uppercase', color: 'var(--team-alt, #f5f5f5)',
        padding: '4px 10px', borderRadius: 4,
        background: 'color-mix(in srgb, var(--team) 30%, transparent)',
        border: '1px solid color-mix(in srgb, var(--team) 60%, transparent)',
      }}>
        Dynasty+ Tools
      </span>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
        <TeamLogo espnId={team.espn_id} logo={team.logo} abbr={team.abbreviation}
                  name={team.name} color={hexColor(team.color)} size={44} plate={false} />
        <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <span style={{
            font: '700 18px "Saira Condensed", sans-serif', letterSpacing: '0.02em',
            textTransform: 'uppercase', color: 'var(--text-1, #e9eef5)',
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {team.name || sim?.user_team || 'No program'}
          </span>
          <span style={{ fontSize: 12, color: 'var(--text-2, #9aa6b2)' }}>
            {active ? `${sim.user_record || '0-0'} (${sim.user_conf_record || '0-0'})` : 'No active season'}
          </span>
        </div>
      </div>

      {active && (
        <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
          <div style={{
            font: '800 22px "Saira Condensed", sans-serif', lineHeight: 1,
            color: 'var(--team-alt, #f5f5f5)',
          }}>
            WK {sim.week}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-2, #9aa6b2)', letterSpacing: '0.08em' }}>
            of {sim.weeks_total || 12}
          </div>
        </div>
      )}
    </header>
  );
}
