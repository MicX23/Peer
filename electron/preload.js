const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('bridgeAPI', {
  // Отправляем команду в Python (fire-and-forget)
  sendCmd: (cmd) => ipcRenderer.send('py:cmd', cmd),
  
  // Слушаем события от Python
  onEvent: (callback) => {
    const handler = (_, data) => callback(data);
    ipcRenderer.on('py:event', handler);
    return () => ipcRenderer.removeListener('py:event', handler);
  }
});