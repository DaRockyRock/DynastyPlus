import SaveImportModal from './SaveImportModal.jsx';

export default {
  title: 'Domain/SaveImportModal',
  component: SaveImportModal,
  parameters: { layout: 'fullscreen' },
};

const saves = [
  {
    save_name: 'DYNASTY-JUL09-06h44m02-AUTOSAVE', save_path: '/saves/a',
    saved_at: '2026-07-09T18:51:00', school: 'Marshall', week_label: 'Week 13',
    has_profile_row: true, registered: true,
  },
  {
    save_name: 'DYNASTY-JUL08-09h34m05-AUTOSAVE', save_path: '/saves/b',
    saved_at: '2026-07-08T22:07:00', school: 'Miami', week_label: 'Week 11',
    has_profile_row: true, registered: false,
  },
  {
    save_name: 'DYNASTY-WEEK3-AUTOSAVE', save_path: '/saves/c',
    saved_at: '2026-07-07T14:45:00', school: null, week_label: null,
    has_profile_row: false, registered: false,
  },
  {
    save_name: 'DYNASTY-NEBRASKAPRESEASON', save_path: '/saves/d',
    saved_at: '2026-07-07T11:48:00', school: null, week_label: null,
    has_profile_row: false, registered: false,
  },
];

const fakeTeams = [
  { name: 'Charlotte 49ers', school: 'Charlotte', conference: 'American', espn_id: 2429, abbreviation: 'CHAR', color: '046a38' },
  { name: 'Nebraska Cornhuskers', school: 'Nebraska', conference: 'Big Ten', espn_id: 158, abbreviation: 'NEB', color: 'e41c38' },
  { name: 'Alabama Crimson Tide', school: 'Alabama', conference: 'SEC', espn_id: 333, abbreviation: 'ALA', color: '9e1b32' },
];

export const Default = {
  render: () => (
    <SaveImportModal
      open
      saves={saves}
      onClose={() => {}}
      onImport={async () => ({ team_name: 'Miami Hurricanes' })}
      loadTeams={async () => fakeTeams}
    />
  ),
};

export const Loading = {
  render: () => <SaveImportModal open loading saves={[]} onClose={() => {}} />,
};

export const Empty = {
  render: () => <SaveImportModal open saves={[]} onClose={() => {}} />,
};
