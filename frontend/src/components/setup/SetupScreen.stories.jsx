import SetupScreen from './SetupScreen.jsx';
import SetupPathRow from './SetupPathRow.jsx';
import SetupArtCard from './SetupArtCard.jsx';

export default {
  title: 'Setup/SetupScreen',
  component: SetupScreen,
  parameters: { layout: 'fullscreen' },
};

export const FirstRun = {
  render: () => (
    <SetupScreen
      title="Set up Dynasty+"
      subtitle="Point the app at your game and pull in its real logos, helmets, and fonts"
      onSkip={() => {}}
      onPrimary={() => {}}
      primaryLabel="Continue"
      primaryDisabled
      footerHint="Extract game art to finish"
    >
      <SetupPathRow
        title="Dynasty saves folder"
        hint="Where College Football 27 keeps your dynasties. Usually found automatically."
        path="C:\\Users\\You\\Documents\\EA SPORTS College Football 27\\saves"
        found
        options={['C:\\Users\\You\\Documents\\EA SPORTS College Football 27\\saves']}
        onBrowse={() => {}}
      />
      <SetupPathRow
        title="College Football 27 install"
        hint="Your installed game, used to read the team art."
        path="C:\\Program Files (x86)\\Steam\\steamapps\\common\\College Football 27"
        found
        onBrowse={() => {}}
      />
      <SetupArtCard installFound onExtract={() => {}} />
    </SetupScreen>
  ),
};

export const Complete = {
  render: () => (
    <SetupScreen
      title="Set up Dynasty+"
      subtitle="You are all set"
      onPrimary={() => {}}
      primaryLabel="Enter Dynasty+"
    >
      <SetupPathRow title="Dynasty saves folder" path="C:\\...\\saves" found onBrowse={() => {}} />
      <SetupArtCard installFound present onExtract={() => {}} />
    </SetupScreen>
  ),
};
