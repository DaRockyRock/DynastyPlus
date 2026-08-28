// Preload bridge: exposes a tiny, safe desktop API to the web UI.
//
// The UI is a normal web app served by the local Flask backend; in the browser
// there is no way to open a native folder picker. Here (running in Electron) we
// expose window.desktop.pickFolder(), backed by the OS "choose folder" dialog,
// so the Setup screen can offer a real "Browse..." button. contextIsolation is
// on, so only what is explicitly bridged is reachable from the page.
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('desktop', {
  isDesktop: true,
  // Opens the native folder picker; resolves to the chosen path, or null if the
  // user cancelled. `title` and `defaultPath` are optional.
  pickFolder: (opts) => ipcRenderer.invoke('dialog:pickFolder', opts || {}),
});
