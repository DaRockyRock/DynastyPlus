// Electron shell for Dynasty+.
//
// Launches the PyInstaller-frozen Flask backend (dynastyplus-backend.exe) as a
// child process, waits for it to answer on its port, then loads the local web
// UI in a desktop window. The backend process is killed when the app quits.
const { app, BrowserWindow, shell, dialog, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');
const net = require('net');

const APP_NAME = 'Dynasty+ Tools';

let backend = null;
let win = null;
let port = 0;              // chosen at launch (free port, avoids dev-server clashes)
let baseUrl = '';

const ZOOM_MIN = 0.5;
const ZOOM_MAX = 2.0;
const ZOOM_STEP = 0.1;

function setZoom(contents, factor) {
  const next = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, factor));
  contents.setZoomFactor(Math.round(next * 10) / 10);
}

function changeZoom(contents, direction) {
  setZoom(contents, contents.getZoomFactor() + direction * ZOOM_STEP);
}

function installZoomControls(contents) {
  // Electron's hidden application menu makes the zoom-in accelerator
  // inconsistent across keyboard layouts. Handle the standard shortcuts
  // directly, including the unshifted Equals key used for Ctrl+Plus.
  contents.on('before-input-event', (event, input) => {
    if (input.type !== 'keyDown' || !(input.control || input.meta)) return;
    if (['+', '=', 'Add'].includes(input.key)) {
      event.preventDefault();
      changeZoom(contents, 1);
    } else if (['-', 'Subtract'].includes(input.key)) {
      event.preventDefault();
      changeZoom(contents, -1);
    } else if (['0', 'Digit0', 'Numpad0'].includes(input.key)) {
      event.preventDefault();
      setZoom(contents, 1);
    }
  });

  // Chromium reports Ctrl+wheel requests here but does not reliably restore
  // the factor after an earlier zoom-out in the packaged window.
  contents.on('zoom-changed', (event, direction) => {
    event.preventDefault();
    changeZoom(contents, direction === 'in' ? 1 : -1);
  });
}

// Ask the OS for an unused local port so the app never collides with a running
// development server or another local process.
function pickFreePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on('error', reject);
    srv.listen(0, '127.0.0.1', () => {
      const chosen = srv.address().port;
      srv.close(() => resolve(chosen));
    });
  });
}

function backendExe() {
  // Packaged: extraResources puts the frozen backend folder at resources/backend.
  // Dev (unpackaged): read the one-folder build produced by scripts/build_app.py.
  const dir = app.isPackaged
    ? path.join(process.resourcesPath, 'backend')
    : path.join(__dirname, '..', 'dist-backend', 'dynastyplus-backend');
  return path.join(dir, 'dynastyplus-backend.exe');
}

function startBackend() {
  const exe = backendExe();
  backend = spawn(exe, [], {
    cwd: path.dirname(exe),
    env: { ...process.env, CFBMOD_PORT: String(port),
           CFBMOD_HOST: '127.0.0.1' },
    stdio: 'ignore',
    windowsHide: true,
  });
  backend.on('error', (err) => {
    dialog.showErrorBox(
      `${APP_NAME} could not start`,
      `Failed to launch the backend service.\n\n${exe}\n\n${err.message}`
    );
    app.quit();
  });
  backend.on('exit', (code) => {
    backend = null;
    // If the backend dies before the window is up, there is nothing to show.
    if (!win && code !== 0 && !app.isQuiting) {
      dialog.showErrorBox(
        `${APP_NAME} stopped`,
        `The backend service exited unexpectedly (code ${code}).`
      );
      app.quit();
    }
  });
}

// Poll the backend's health endpoint until it answers (or we give up).
function waitForBackend(timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(`${baseUrl}/api/config`, (res) => {
        res.resume();
        resolve();
      });
      req.on('error', () => {
        if (Date.now() > deadline) {
          reject(new Error('backend did not become ready in time'));
        } else {
          setTimeout(tick, 250);
        }
      });
    };
    tick();
  });
}

function createWindow() {
  win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 680,
    title: APP_NAME,
    backgroundColor: '#0a0e14',
    show: false,
    autoHideMenuBar: true,
    icon: path.join(__dirname, 'build', 'icon.ico'),
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  win.once('ready-to-show', () => win.show());
  win.loadURL(`${baseUrl}/`);
  installZoomControls(win.webContents);

  // Open external links (mailto, http to other hosts) in the system browser.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith(baseUrl)) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  win.on('closed', () => { win = null; });
}

// A second launch focuses the existing window.
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (win) {
      if (win.isMinimized()) win.restore();
      win.focus();
    }
  });

  app.setName(APP_NAME);

  // Native folder picker for the Setup screen (window.desktop.pickFolder).
  // openAtParent: open the dialog in defaultPath's PARENT so the target folder
  // is a visible, single-clickable item. A directory picker hides files, so
  // opening INSIDE a folder that holds only files (the game's saves folder)
  // renders as "No items match your search" and reads as missing saves.
  ipcMain.handle('dialog:pickFolder', async (_evt, opts = {}) => {
    let at = opts.defaultPath || undefined;
    if (at && opts.openAtParent) {
      const parent = path.dirname(at);
      if (parent && parent !== at) at = parent;
    }
    const result = await dialog.showOpenDialog(win || undefined, {
      title: opts.title || 'Select folder',
      defaultPath: at,
      properties: ['openDirectory'],
    });
    if (result.canceled || !result.filePaths.length) return null;
    return result.filePaths[0];
  });

  app.whenReady().then(async () => {
    try {
      port = await pickFreePort();
      baseUrl = `http://127.0.0.1:${port}`;
    } catch (err) {
      dialog.showErrorBox(`${APP_NAME} could not start`,
        `Could not find a free local port.\n\n${err.message}`);
      app.quit();
      return;
    }
    startBackend();
    try {
      await waitForBackend();
    } catch (err) {
      dialog.showErrorBox(
        `${APP_NAME} could not start`,
        `The backend service did not respond.\n\n${err.message}`
      );
      app.quit();
      return;
    }
    createWindow();

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
  });
}

app.on('window-all-closed', () => {
  app.quit();
});

// Make sure the backend never outlives the app.
function stopBackend() {
  if (backend && !backend.killed) {
    backend.kill();
    backend = null;
  }
}
app.on('before-quit', () => { app.isQuiting = true; stopBackend(); });
app.on('will-quit', stopBackend);
process.on('exit', stopBackend);
