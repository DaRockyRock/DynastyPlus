import SaveFileRow from './SaveFileRow.jsx';

export default {
  title: 'Domain/SaveFileRow',
  component: SaveFileRow,
  parameters: { layout: 'padded' },
};

const base = {
  save_name: 'DYNASTY-JUL09-06h44m02-AUTOSAVE',
  saved_at: '2026-07-09T18:51:00',
  school: 'Marshall',
  week_label: 'Week 13',
  has_profile_row: true,
  registered: false,
};

const wrap = (el) => <div style={{ width: 560 }}>{el}</div>;

export const KnownTeam = { render: () => wrap(<SaveFileRow save={base} onImport={() => {}} />) };

export const AlreadyImported = {
  render: () => wrap(<SaveFileRow save={{ ...base, registered: true }} onImport={() => {}} />),
};

export const UnknownTeam = {
  render: () => wrap(<SaveFileRow
    save={{ ...base, save_name: 'DYNASTY-WEEK3', school: null, week_label: null, has_profile_row: false }}
    onImport={() => {}}
  />),
};

export const Importing = {
  render: () => wrap(<SaveFileRow save={base} onImport={() => {}} busy />),
};
