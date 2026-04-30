const { app, BrowserWindow, ipcMain, shell } = require('electron'); // <--- ДОБАВИТЬ shell
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

const isDev = process.env.NODE_ENV !== 'production';
// Берем порт из переменной среды VITE_PORT, если нет - используем 5173 по умолчанию
const vitePort = process.env.VITE_PORT || '5173'; 
const devUrl = `http://localhost:${vitePort}`;

let pyProc, mainWindow, buffer = '';

// 1. Ищем Python внутри venv
function getPythonPath() {
  const root = path.join(__dirname, '..'); 
  const winVenv = path.join(root, '.venv', 'Scripts', 'python.exe');
  const unixVenv = path.join(root, '.venv', 'bin', 'python');
  
  if (fs.existsSync(winVenv)) return winVenv;
  if (fs.existsSync(unixVenv)) return unixVenv;
  return 'python';
}

function startPython() {
  const pythonPath = getPythonPath();
  const pyScript = path.join(__dirname, '../backend/main.py');
  const workDir = path.join(__dirname, '../backend');

  console.log(`[Electron] Using Python: ${pythonPath}`);

  const electronDataDir = app.getPath('userData'); 
  
  console.log(`[Electron] User Data Dir: ${electronDataDir}`);

  pyProc = spawn(pythonPath, [pyScript, electronDataDir], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    cwd: path.join(__dirname, '../backend') // Рабочая директория Python - backend
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

// --- НОВЫЕ ОБРАБОТЧИКИ ДЛЯ ФАЙЛОВ ---

ipcMain.handle('open-file', async (event, filePath) => {
  console.log('[Main] Received relative path:', filePath);

  if (!filePath) {
    throw new Error('Путь к файлу пуст');
  }

  try {
    // ПРЕОБРАЗУЕМ ОТНОСИТЕЛЬНЫЙ ПУТЬ В АБСОЛЮТНЫЙ
    // path.resolve() сделает из "./downloads/file.txt" -> "F:/_Diploms/Peer/downloads/file.txt"
    const absolutePath = path.resolve(filePath);
    
    console.log('[Main] Resolved absolute path:', absolutePath);

    // Опционально: Проверка существования файла перед открытием
    if (!fs.existsSync(absolutePath)) {
       throw new Error(`Файл не найден по пути: ${absolutePath}`);
    }

    const result = await shell.openPath(absolutePath);
    
    if (result) {
      console.error(`[Main] Shell error: ${result}`);
      throw new Error(result);
    }
    return 'success';
  } catch (error) {
    console.error('[Main] Failed to open file:', error);
    throw error;
  }
});

ipcMain.handle('show-item-in-folder', async (event, filePath) => {
  console.log('[Main] Received relative path for folder:', filePath);

  if (!filePath) {
    throw new Error('Путь к файлу пуст');
  }

  try {
    // ПРЕОБРАЗУЕМ ОТНОСИТЕЛЬНЫЙ ПУТЬ В АБСОЛЮТНЫЙ
    const absolutePath = path.resolve(filePath);
    console.log('[Main] Resolved absolute path:', absolutePath);

    // Для showItemInFolder тоже лучше проверить существование, 
    // хотя он просто открывает проводник. Если файла нет, проводник может открыть родительскую папку или ничего.
    if (!fs.existsSync(absolutePath)) {
        console.warn(`[Main] File does not exist at: ${absolutePath}`);
        // Можно решить, выбрасывать ошибку или нет. Обычно лучше показать предупреждение.
    }

    shell.showItemInFolder(absolutePath);
    return 'success';
  } catch (error) {
    console.error('[Main] Failed to show in folder:', error);
    throw error;
  }
});

// -------------------------------

ipcMain.on('py:cmd', (_, cmd) => sendToPy(cmd));
app.on('before-quit', () => pyProc?.kill());