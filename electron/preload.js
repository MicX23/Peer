const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Эти имена должны точно совпадать с ipcMain.handle в main.js
  openFile: (filePath) => ipcRenderer.invoke('open-file', filePath),
  showItemInFolder: (filePath) => ipcRenderer.invoke('show-item-in-folder', filePath),
});

contextBridge.exposeInMainWorld('bridgeAPI', {
  sendCmd: (cmd) => ipcRenderer.send('py:cmd', cmd),
  onEvent: (callback) => {
    const handler = (_, data) => callback(data);
    ipcRenderer.on('py:event', handler);
    return () => ipcRenderer.removeListener('py:event', handler);
  }
});