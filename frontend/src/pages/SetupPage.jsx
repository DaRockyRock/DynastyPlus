import { useState } from 'react';
import { useApp } from '../context/AppContext.jsx';
import { SetupScreen, SetupPathRow, SetupArtCard } from '../components/index.js';

// First-run Setup. Points Dynasty+ at the game's saves folder
// and install, and pulls the real team art in one click. Both locations are
// auto-detected; a native "Browse..." button covers anything unusual. The user
// can continue at any time (the app falls back to monogram marks without art).
export default function SetupPage() {
  const { setup, browseFolder, setSavePath, setGameRoot, runExtraction, closeSetup } = useApp();
  const [browsing, setBrowsing] = useState(null);

  const s = setup || {};
  const detected = s.detected || { installs: [], saves: [] };
  const complete = !!(s.save_path_exists && s.art_present);

  const pickSaves = async () => {
    setBrowsing('save');
    try {
      // openAtParent: the saves folder holds only files, which a folder picker
      // hides; opening inside it looks empty ("No items match your search").
      // Opening one level up shows "saves" as an item to single-click instead.
      const p = await browseFolder({
        title: 'Select your College Football 27 saves folder',
        defaultPath: s.save_path,
        openAtParent: true,
      });
      if (p) await setSavePath(p);
    } finally { setBrowsing(null); }
  };

  const pickGame = async () => {
    setBrowsing('game');
    try {
      const p = await browseFolder({ title: 'Select your College Football 27 install folder', defaultPath: s.game_root });
      if (p) await setGameRoot(p);
    } finally { setBrowsing(null); }
  };

  return (
    <SetupScreen
      title="Set up Dynasty+"
      subtitle="Point the app at your game, then pull in its real logos, helmets, and fonts"
      onPrimary={closeSetup}
      primaryLabel={complete ? 'Enter Dynasty+' : 'Continue anyway'}
      footerHint={!complete && !s.art_present ? 'Extract game art to finish setup' : undefined}
    >
      <SetupPathRow
        title="Dynasty saves folder"
        hint="Where College Football 27 keeps your dynasties. This is usually found for you; the app reads (never changes) these saves when you Scan. Heads up: the folder picker lists folders only, so your DYNASTY save files will not appear inside it. Select the saves folder itself."
        path={s.save_path}
        found={!!s.save_path_exists}
        options={detected.saves}
        onChoose={setSavePath}
        onBrowse={browseFolder ? pickSaves : undefined}
        browsing={browsing === 'save'}
      />
      <SetupPathRow
        title="College Football 27 install"
        hint="Your installed game. The app reads the team art from here; it stays on your computer."
        path={s.game_root}
        found={!!s.game_root_exists}
        options={detected.installs}
        onChoose={setGameRoot}
        onBrowse={browseFolder ? pickGame : undefined}
        browsing={browsing === 'game'}
      />
      <SetupArtCard
        present={!!s.art_present}
        installFound={!!s.game_root_exists}
        extracting={!!s.extracting}
        stage={s.stage}
        done={s.done}
        total={s.total}
        error={s.error}
        onExtract={() => runExtraction()}
      />
    </SetupScreen>
  );
}
