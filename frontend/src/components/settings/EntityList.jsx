import { useState } from 'react';
import EntityCard from './EntityCard.jsx';
import { useSettingsMeta } from './SettingsContext.jsx';
import { PlusIcon } from '../ui/icons.jsx';

// Build a blank record for a section from its field defaults (used by Add).
function blankItem(section) {
  const item = {};
  section.fields.forEach((f) => {
    const def = f.type === 'stars' || f.type === 'percent' || f.type === 'number' || f.type === 'rating' || f.type === 'year'
      ? '' : (f.type === 'select' ? (f.options?.[0]?.value ?? '') : '');
    // dot-path defaults (e.g. entity.kind)
    if (f.key.includes('.')) {
      const [head, tail] = f.key.split('.');
      item[head] = { ...(item[head] || {}), [tail]: def };
    } else {
      item[f.key] = def;
    }
  });
  return item;
}

// Editor for a list section: a count/add bar, a stack of EntityCards, and an
// Add button. Owns only which row is expanded; all data lives in the parent.
export default function EntityList({ section, items = [], onChange, onUpload }) {
  const [openIdx, setOpenIdx] = useState(null);
  const meta = useSettingsMeta();

  const replace = (next, nextOpen) => { onChange(next); if (nextOpen !== undefined) setOpenIdx(nextOpen); };
  const update = (i, item) => replace(items.map((it, j) => (j === i ? item : it)));
  const remove = (i) => replace(items.filter((_, j) => j !== i), null);
  const duplicate = (i) => {
    const copy = JSON.parse(JSON.stringify(items[i]));
    const next = [...items.slice(0, i + 1), copy, ...items.slice(i + 1)];
    replace(next, i + 1);
  };
  const move = (i, dir) => {
    const j = i + dir;
    if (j < 0 || j >= items.length) return;
    const next = [...items];
    [next[i], next[j]] = [next[j], next[i]];
    replace(next, openIdx === i ? j : openIdx === j ? i : openIdx);
  };
  const add = async () => {
    let item = blankItem(section);
    // A new person gets a personality + bio the moment they hit the board.
    if (section.persona && meta.generatePerson) {
      try {
        const res = await meta.generatePerson(section.key, { name: item.name });
        item = { ...item, traits: res.traits, bio: res.bio };
      } catch { /* the backend fills persona on save/reload as a fallback */ }
    }
    const next = [...items, item];
    replace(next, next.length - 1);
  };

  return (
    <div>
      <div className="set-list-bar">
        <span className="set-list-count">{items.length} {items.length === 1 ? (section.item_kind || 'item') : `${section.item_kind || 'item'}s`}</span>
      </div>
      <div className="set-list">
        {items.length === 0 && <div className="set-list-empty">No {section.item_kind || 'item'}s yet. Add one below.</div>}
        {items.map((item, i) => (
          <EntityCard
            key={i}
            section={section}
            item={item}
            index={i}
            total={items.length}
            open={openIdx === i}
            onToggle={() => setOpenIdx(openIdx === i ? null : i)}
            onChange={(it) => update(i, it)}
            onRemove={() => remove(i)}
            onDuplicate={() => duplicate(i)}
            onMoveUp={() => move(i, -1)}
            onMoveDown={() => move(i, 1)}
            onUpload={onUpload}
          />
        ))}
        <button className="set-add" type="button" onClick={add}>
          <PlusIcon />Add {section.item_kind || 'item'}
        </button>
      </div>
    </div>
  );
}
