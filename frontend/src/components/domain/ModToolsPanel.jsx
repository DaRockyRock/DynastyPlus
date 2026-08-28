import { useState } from 'react';
import PanelCard from '../ui/PanelCard.jsx';
import Button from '../ui/Button.jsx';
import { CheckIcon, ImageIcon, AlertIcon, FolderIcon } from '../ui/icons.jsx';

// Setup + handoff card for in-game mods via the MMC Modding Tools (the
// College Football Modding Community's Frosty fork). Dynasty+ detects the
// tools, exports custom conference logos as a .fbmod into the Mod Manager's
// library on Save, and the manager owns applying mods and launching the
// game. Three states, driven by /api/modtools/status: tools not found (point
// the app at the extracted folder), anti-cheat swap pending (the one manual
// step, explained), and ready (open the manager, apply, play). Presentational:
// the page owns all state and calls.
export default function ModToolsPanel({ status, onLocate, onOpenManager, onRefresh, exportResult, busy }) {
  const [path, setPath] = useState('');
  if (!status) return null;

  const offlineNote = (
    <span className="cs-modsetup-note">
      Mods are for offline play only, never Online Dynasty. Restore the original
      anti-cheat file to play online again.
    </span>
  );

  if (!status.tools_found) {
    return (
      <PanelCard className="cs-modsetup" title="In-Game Logos">
        <div className="cs-modsetup-row">
          <span className="cs-modsetup-ico" aria-hidden="true"><ImageIcon /></span>
          <span className="cs-modsetup-text">
            Custom conference logos load in game through the <b>MMC Modding Tools</b>,
            the free community modding kit for CFB 27. Once Dynasty+ knows where they
            are, every Save exports your logos as a ready-to-play mod.
          </span>
        </div>
        <ol className="cs-modsetup-steps">
          <li>Download the MMC Modding Tools from the College Football Modding Community (<code>discord.gg/cfmc</code>) and extract the archive anywhere.</li>
          <li>Paste the extracted folder&apos;s path here:</li>
        </ol>
        <div className="cs-modsetup-path">
          <input
            className="set-input"
            value={path}
            placeholder="C:\...\MMC_Modding_Tools_v1.1.0.0"
            onChange={(e) => setPath(e.target.value)}
          />
          <Button onClick={() => onLocate?.(path)} disabled={busy || !path.trim()}>
            <FolderIcon /> Use this folder
          </Button>
        </div>
      </PanelCard>
    );
  }

  if (status.anticheat !== 'stub') {
    return (
      <PanelCard className="cs-modsetup" title="In-Game Logos">
        <div className="cs-modsetup-row">
          <span className="cs-modsetup-ico ok" aria-hidden="true"><CheckIcon /></span>
          <span className="cs-modsetup-text">
            MMC Modding Tools found at <code>{status.tools_path}</code>. One manual
            step remains before the game will load mods: swap the anti-cheat
            launcher for the tools&apos; modded one.
          </span>
        </div>
        <ol className="cs-modsetup-steps">
          <li>Open your game folder: <code>{status.game_root}</code></li>
          <li>Rename <b>{status.anticheat_exe}</b> to <b>_{status.anticheat_exe}</b> (this is your backup for playing online).</li>
          <li>Copy the <b>{status.anticheat_exe}</b> from the tools&apos; <b>AC</b> folder into the game folder.</li>
          <li>Come back and check again.</li>
        </ol>
        <div className="cs-modsetup-actions">
          <Button onClick={onRefresh} disabled={busy}>Check again</Button>
          <span className="cs-modsetup-warn"><AlertIcon /> Requires editing the game install</span>
        </div>
        {offlineNote}
      </PanelCard>
    );
  }

  const installed = status.installed_mods?.length > 0 || !!exportResult?.installed_to;
  return (
    <PanelCard className="cs-modsetup done" title="In-Game Logos">
      <div className="cs-modsetup-row">
        <span className="cs-modsetup-ico ok" aria-hidden="true"><CheckIcon /></span>
        <span className="cs-modsetup-text">
          MMC Modding Tools ready.
          {installed
            ? <> Your logo mod is in the Mod Manager&apos;s library{exportResult?.conferences?.length ? <> ({exportResult.conferences.join(', ')})</> : null} and refreshes on every Save.</>
            : <> Saving with a custom logo exports <b>DynastyPlus Conference Logos.fbmod</b> straight into the Mod Manager&apos;s library.</>}
        </span>
      </div>
      <ol className="cs-modsetup-steps">
        <li>Open the <b>MMC Mod Manager</b> and select the CFB 27 profile.</li>
        <li>Enable <b>DynastyPlus Conference Logos</b> in your pack, then press <b>Apply</b>.</li>
        <li>Press <b>Launch</b> in the manager to start the game with your logos.</li>
      </ol>
      <div className="cs-modsetup-actions">
        <Button variant="accent" onClick={onOpenManager} disabled={busy}>Open Mod Manager</Button>
      </div>
      {offlineNote}
    </PanelCard>
  );
}
