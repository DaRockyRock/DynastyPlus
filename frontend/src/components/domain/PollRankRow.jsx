import TeamLogo from '../ui/TeamLogo.jsx';
import { ChevronUp, ChevronDown, CloseIcon } from '../ui/icons.jsx';

// One row of the poll editor's ranking list: rank number, real logo, team,
// record, and (in editable mode) reorder controls plus native drag support.
// `delta` (from an algorithm preview) renders as a movement tag vs the save's
// current poll: positive = the algorithm ranks the team higher than the game.
export default function PollRankRow({
  entry,
  isUser = false,
  editable = false,
  onMoveUp,
  onMoveDown,
  onRemove,
  dragging = false,
  dragOver = false,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
}) {
  const delta = entry.delta;
  return (
    <div
      className={[
        'poll-row',
        isUser ? 'is-user' : '',
        editable ? 'is-editable' : '',
        dragging ? 'is-dragging' : '',
        dragOver ? 'is-drag-over' : '',
      ].filter(Boolean).join(' ')}
      draggable={editable || undefined}
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onDragEnd={onDragEnd}
    >
      {editable && <span className="poll-row-grip" aria-hidden="true">::</span>}
      <span className="poll-row-num">{entry.rank}</span>
      <TeamLogo espnId={entry.espn_id} logo={entry.logo} abbr={entry.abbr} name={entry.team} size={22} />
      <span className="poll-row-team">{entry.school || entry.team}</span>
      <span className="poll-row-rec">{entry.record}</span>
      {delta != null && delta !== 0 && (
        <span className={`poll-row-delta ${delta > 0 ? 'up' : 'down'}`}>
          {delta > 0 ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {Math.abs(delta)}
        </span>
      )}
      {editable && (
        <span className="poll-row-actions">
          <button className="poll-row-btn" title="Move up" onClick={onMoveUp} disabled={!onMoveUp}>
            <ChevronUp size={14} />
          </button>
          <button className="poll-row-btn" title="Move down" onClick={onMoveDown} disabled={!onMoveDown}>
            <ChevronDown size={14} />
          </button>
          {onRemove && (
            <button className="poll-row-btn poll-row-btn-remove" title="Drop from the ranking" onClick={onRemove}>
              <CloseIcon size={13} />
            </button>
          )}
        </span>
      )}
    </div>
  );
}
