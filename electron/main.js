const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

let pyProc, mainWindow, buffer = '';

// 1. Ищем Python внутри venv
function getPythonPath() {
  const root = path.join(__dirname, '..'); // Корень проекта
  const winVenv = path.join(root, '.venv', 'Scripts', 'python.exe');
  const unixVenv = path.join(root, '.venv', 'bin', 'python');
  
  if (fs.existsSync(winVenv)) return winVenv;
  if (fs.existsSync(unixVenv)) return unixVenv;
  return 'python'; // Fallback
}

function startPython() {
  const pythonPath = getPythonPath();
  const pyScript = path.join(__dirname, '../backend/main.py');
  const workDir = path.join(__dirname, '../backend');

  console.log(`[Electron] Using Python: ${pythonPath}`);

  pyProc = spawn(pythonPath, [pyScript], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    cwd: workDir // Важно для работы относительных путей в Node/User
  });

  pyProc.stdout.setEncoding('utf8');
  pyProc.stdout.on('data', (chunk) => {
    buffer += chunk;
    const lines = buffer.split('\n');
    buffer = lines.pop();
    
    lines.forEach(line => {
      if (!line.trim()) return;
      try {
        const msg = JSON.parse(line);
        // Логируем для отладки
        console.log('[Py->JS]:', msg); 
        mainWindow?.webContents.send('py:event', msg);
      } catch (e) {
        console.error('[Electron] Invalid JSON:', line);
      }
    });
  });

  pyProc.stderr.on('data', (d) => console.error('[Py STDERR]:', d.toString()));
  pyProc.on('close', (code) => console.log(`[Electron] Python exited: ${code}`));
  pyProc.on('error', (err) => console.error('[Electron] Spawn error:', err));
}

function sendToPy(cmd) {
  if (pyProc?.stdin?.writable) {
    pyProc.stdin.write(JSON.stringify(cmd) + '\n');
  }
}

app.whenReady().then(() => {
  startPython();
  mainWindow = new BrowserWindow({
    width: 900, height: 700,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  const isDev = process.env.NODE_ENV !== 'production';
  mainWindow.loadURL(isDev ? 'http://localhost:5173' : `file://${path.join(__dirname, '../frontend/dist/index.html')}`);
});

ipcMain.on('py:cmd', (_, cmd) => sendToPy(cmd));
app.on('before-quit', () => pyProc?.kill());