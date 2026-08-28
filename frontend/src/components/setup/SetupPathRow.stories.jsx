import SetupPathRow from './SetupPathRow.jsx';

export default {
  title: 'Setup/SetupPathRow',
  component: SetupPathRow,
};

export const Found = {
  args: {
    title: 'Dynasty saves folder',
    hint: 'Where College Football 27 keeps your dynasties. Usually found automatically.',
    path: 'C:\\Users\\You\\Documents\\EA SPORTS College Football 27\\saves',
    found: true,
    options: [
      'C:\\Users\\You\\Documents\\EA SPORTS College Football 27\\saves',
      'C:\\Users\\You\\OneDrive\\Documents\\EA SPORTS College Football 27\\saves',
    ],
    onBrowse: () => {},
    onChoose: () => {},
  },
};

export const NotFound = {
  args: {
    title: 'College Football 27 install',
    hint: 'Your installed game, used to read the team art.',
    path: '',
    found: false,
    options: [],
    onBrowse: () => {},
  },
};
