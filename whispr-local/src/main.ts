import { app, BrowserWindow, ipcMain, Menu, nativeImage, Tray } from "electron";
import { spawn, ChildProcessWithoutNullStreams } from "node:child_process";
import { createInterface } from "node:readline";
import path from "node:path";
import { screen } from "electron";

declare const __WHISPR_BACKEND_ROOT__: string;
declare const __WHISPR_PYTHON__: string;

let window: BrowserWindow | null = null;
let tray: Tray | null = null;
let backend: ChildProcessWithoutNullStreams | null = null;
const backendRoot = app.isPackaged ? __WHISPR_BACKEND_ROOT__ : process.cwd();
const python = app.isPackaged ? __WHISPR_PYTHON__ : (process.env.WHISPR_PYTHON || path.join(backendRoot, ".venv", "bin", "python"));

function sendStatus(state: string, detail: string): void {
  if (window && !window.isDestroyed()) window.webContents.send("status", { state, detail });
}

function startBackend(): void {
  const script = path.join(backendRoot, "main.py");
  const child = spawn(python, [script, "--daemon-ui"], { cwd: backendRoot, stdio: ["pipe", "pipe", "pipe"] });
  backend = child;
  const lines = createInterface({ input: child.stdout });
  lines.on("line", (line) => {
    try {
      const message = JSON.parse(line);
      if (message.type === "status") sendStatus(message.state, message.detail);
    } catch {
      // Ignore non-status output so the UI stays responsive if the backend logs.
    }
  });
  child.on("error", (error) => sendStatus("error", `Backend failed to start: ${error.message}`));
  child.on("exit", (code) => {
    backend = null;
    if (code !== 0 && code !== null) sendStatus("error", "Dictation backend stopped");
  });
}

function command(type: "toggle" | "quit"): void {
  backend?.stdin.write(`${JSON.stringify({ type })}\n`);
}

function createWindow(): void {
  window = new BrowserWindow({
    width: 380,
    height: 58,
    x: Math.max(0, Math.round((screen.getPrimaryDisplay().workAreaSize.width - 380) / 2)),
    y: 48,
    frame: false,
    transparent: true,
    resizable: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    focusable: false,
    hasShadow: false,
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, nodeIntegration: false },
  });
  window.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  window.setAlwaysOnTop(true, "floating");
  void window.loadFile(path.join(__dirname, "index.html"));
  window.on("closed", () => { window = null; });
}

app.whenReady().then(() => {
  app.dock?.hide();
  createWindow();
  startBackend();
  const icon = nativeImage.createEmpty();
  tray = new Tray(icon);
  tray.setTitle("Whispr");
  tray.setToolTip("Whispr Local — hold Space to dictate");
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: "Start / stop dictation", click: () => command("toggle") },
    { type: "separator" },
    { label: "Quit Whispr Local", click: () => app.quit() },
  ]));
});

ipcMain.on("toggle", () => command("toggle"));
app.on("before-quit", () => { command("quit"); backend?.kill("SIGTERM"); });
app.on("window-all-closed", () => {});
