import KeyValue from '../ui/KeyValue.jsx';
import PersonName from '../people/PersonName.jsx';

// One portal movement line (incoming / outgoing / target).
export default function MoveRow({ player, kind = 'in' }) {
  const dest = kind === 'out' ? (player.to || 'Undecided') : (player.from || '');
  const label = kind === 'out' ? 'to' : 'from';
  return (
    <KeyValue
      k={(
        <span>
          <b style={{ color: 'var(--text)' }}><PersonName name={player.name} kind="transfer" /></b>{' '}
          <span style={{ color: 'var(--text-3)' }}>{player.position || ''}</span>{' '}
          <span style={{ fontSize: 11 }}>{label} {dest}</span>
        </span>
      )}
      v={player.grade || player.fit || player.impact || player.lean || player.reason || ''}
    />
  );
}
