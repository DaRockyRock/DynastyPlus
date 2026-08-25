import Avatar from '../ui/Avatar.jsx';
import TeamLogo from '../ui/TeamLogo.jsx';
import FieldGrid from './FieldGrid.jsx';
import { ChevronDown, CopyIcon, TrashIcon } from '../ui/icons.jsx';
import { getPath } from '../../lib/objectPath.js';

// One record in a list section. Collapsed: avatar + title/subtitle + row actions
// (move, duplicate, delete). Expanded: the full field grid. `section` carries
// the field defs plus which keys drive the title/subtitle/avatar.
export default function EntityCard({
  section, item, index, total, open, onToggle, onChange,
  onRemove, onDuplicate, onMoveUp, onMoveDown, onUpload,
}) {
  const title = getPath(item, section.title_field || 'name');
  const subtitle = section.subtitle_field ? getPath(item, section.subtitle_field) : '';
  const image = section.image_field ? getPath(item, section.image_field) : '';
  const isTeam = !!section.team_field;

  const stop = (fn) => (e) => { e.stopPropagation(); fn(); };

  const avatar = image
    ? <span className="avatar" style={{ overflow: 'hidden' }}><img src={image} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /></span>
    : isTeam
      ? <TeamLogo name={title} size={40} />
      : <Avatar name={title || '?'} size={40} gradient />;

  return (
    <div className={`entity-card${open ? ' open' : ''}`}>
      <div className="ec-head" onClick={onToggle} role="button" tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle(); } }}>
        <span className="ec-avatar">{avatar}</span>
        <span className="ec-id">
          <span className={`ec-title${title ? '' : ' placeholder'}`}>{title || `New ${section.item_kind || 'item'}`}</span>
          {subtitle ? <span className="ec-sub">{subtitle}</span> : null}
        </span>
        <span className="ec-acts">
          <button className="ec-act" title="Move up" onClick={stop(onMoveUp)} disabled={index === 0}>↑</button>
          <button className="ec-act" title="Move down" onClick={stop(onMoveDown)} disabled={index === total - 1}>↓</button>
          <button className="ec-act" title="Duplicate" onClick={stop(onDuplicate)}><CopyIcon /></button>
          <button className="ec-act danger" title="Delete" onClick={stop(onRemove)}><TrashIcon /></button>
          <span className="ec-act ec-chev"><ChevronDown /></span>
        </span>
      </div>
      {open && (
        <div className="ec-body">
          <FieldGrid fields={section.fields} value={item} onChange={onChange} onUpload={onUpload} />
        </div>
      )}
    </div>
  );
}
