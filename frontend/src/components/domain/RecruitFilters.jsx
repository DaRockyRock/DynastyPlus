import TextInput from '../ui/TextInput.jsx';
import Select from '../ui/Select.jsx';
import SegmentedControl from '../ui/SegmentedControl.jsx';

// Filter bar for the national recruit board: name search, position, star
// minimum, and commitment status. `value` is { q, position, stars, status }.
const POSITIONS = ['QB', 'RB', 'WR', 'TE', 'OT', 'IOL', 'EDGE', 'DT', 'LB', 'CB', 'S', 'ATH'];
const STAR_OPTS = [
  { value: '0', label: 'All stars' }, { value: '5', label: '5 star' },
  { value: '4', label: '4 star and up' }, { value: '3', label: '3 star and up' },
];
const STATUS_OPTS = [
  { value: 'all', label: 'All' }, { value: 'open', label: 'Open' },
  { value: 'committed', label: 'Committed' }, { value: 'signed', label: 'Signed' },
];

export default function RecruitFilters({ value, onChange, count }) {
  const v = value || { q: '', position: '', stars: '0', status: 'all' };
  const set = (key) => (val) => onChange?.({ ...v, [key]: val });
  return (
    <div className="rb-filters">
      <TextInput className="rb-search" placeholder="Search recruits" value={v.q} onValueChange={set('q')} />
      <Select
        value={v.position}
        onValueChange={set('position')}
        options={[{ value: '', label: 'All positions' }, ...POSITIONS.map((p) => ({ value: p, label: p }))]}
      />
      <Select value={v.stars} onValueChange={set('stars')} options={STAR_OPTS} />
      <SegmentedControl options={STATUS_OPTS} value={v.status} onChange={set('status')} />
      {count != null && <span className="rb-count">{count} prospects</span>}
    </div>
  );
}
