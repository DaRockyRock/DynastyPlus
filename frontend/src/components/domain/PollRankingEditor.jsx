import { useState } from 'react';
import Select from '../ui/Select.jsx';
import PollRankRow from './PollRankRow.jsx';

// The manual-mode ranking editor: an ordered list of teams the user drags
// (or nudges with the arrows) into their own poll. Only the head list is
// user-ordered; every team below it keeps the game's relative order, so the
// footer picker can promote any unlisted team into the ranking.
//
// `entries` is the user's current head order as full entry objects
// ({ team, school, abbr, record, espn_id }); `onChange` receives the new
// array after any reorder/add/remove.
export default function PollRankingEditor({
  entries = [],
  onChange,
  userTeam,
  addOptions = [],
}) {
  const [dragIndex, setDragIndex] = useState(null);
  const [overIndex, setOverIndex] = useState(null);

  const move = (from, to) => {
    if (to < 0 || to >= entries.length || from === to) return;
    const next = entries.slice();
    const [row] = next.splice(from, 1);
    next.splice(to, 0, row);
    onChange?.(next);
  };

  const removeAt = (i) => {
    const next = entries.slice();
    next.splice(i, 1);
    onChange?.(next);
  };

  const add = (name) => {
    if (!name) return;
    const pick = addOptions.find((o) => o.team === name);
    if (pick) onChange?.([...entries, pick]);
  };

  const drop = (i) => {
    if (dragIndex != null && dragIndex !== i) move(dragIndex, i);
    setDragIndex(null);
    setOverIndex(null);
  };

  return (
    <div className="poll-editor-list">
      {entries.map((e, i) => (
        <PollRankRow
          key={e.team}
          entry={{ ...e, rank: i + 1 }}
          isUser={e.team === userTeam}
          editable
          onMoveUp={i > 0 ? () => move(i, i - 1) : undefined}
          onMoveDown={i < entries.length - 1 ? () => move(i, i + 1) : undefined}
          onRemove={() => removeAt(i)}
          dragging={dragIndex === i}
          dragOver={overIndex === i && dragIndex !== i}
          onDragStart={() => setDragIndex(i)}
          onDragOver={(ev) => { ev.preventDefault(); setOverIndex(i); }}
          onDrop={() => drop(i)}
          onDragEnd={() => { setDragIndex(null); setOverIndex(null); }}
        />
      ))}
      <div className="poll-editor-foot">
        {addOptions.length > 0 && (
          <Select
            value=""
            onValueChange={add}
            options={[{ value: '', label: 'Add a team to the ranking...' },
              ...addOptions.map((o) => ({ value: o.team, label: `${o.school || o.team} (${o.record})` }))]}
          />
        )}
        <p className="poll-editor-note">
          Teams below this list keep the game's own order.
        </p>
      </div>
    </div>
  );
}
