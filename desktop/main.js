/**
 * Manhattan Mission Control — Electron main process.
 *
 * Wraps the self-contained mission_control_v2 SPA in a native desktop shell:
 *   - secure BrowserWindow (context isolation, no node integration in renderer)
 *   - native application menu + system tray
 *   - persisted window bounds
 *   - auto-update via electron-updater (GitHub releases)
 *   - external links open in the system browser
 *   - optional Python FastAPI sidecar for ML-heavy endpoints (off by default)
 */

const {
  app,
  BrowserWindow,
  Menu,
  Tray,
  shell,
  ipcMain,
  dialog,
  nativeTheme,
} = require("electron");
const path = require("path");
const Store = require("electron-store");
const { autoUpdater } = require("electron-updater");

const store = new Store({ name: "window-state" });
const isDev = !app.isPackaged;

let mainWindow = null;
let tray = null;
let sidecar = null; // optional Python backend process

// ---------------------------------------------------------------------------
// SPA path resolution
// ---------------------------------------------------------------------------
function rendererIndex() {
  // In dev, load the canonical SPA from the repo; in prod, the copied bundle.
  if (isDev) {
    return path.join(__dirname, "..", "app", "static", "mission_control_v2.html");
  }
  return path.join(__dirname, "renderer", "index.html");
}

// ---------------------------------------------------------------------------
// Window
// ---------------------------------------------------------------------------
function createWindow() {
  const bounds = store.get("bounds", { width: 1480, height: 940 });

  mainWindow = new BrowserWindow({
    ...bounds,
    minWidth: 1024,
    minHeight: 680,
    backgroundColor: "#0a1628",
    title: "Manhattan Mission Control",
    show: false,
    autoHideMenuBar: false,
    icon: path.join(__dirname, "build", process.platform === "win32" ? "icon.ico" : "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      spellcheck: true,
    },
  });

  mainWindow.loadFile(rendererIndex());

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
    if (store.get("maximized")) mainWindow.maximize();
  });

  // Persist window state
  const saveBounds = () => {
    if (!mainWindow.isMaximized()) store.set("bounds", mainWindow.getBounds());
    store.set("maximized", mainWindow.isMaximized());
  };
  mainWindow.on("resize", saveBounds);
  mainWindow.on("move", saveBounds);
  mainWindow.on("close", saveBounds);
  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  // Security: open external links in the system browser, never in-app.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http:") || url.startsWith("https:")) {
      shell.openExternal(url);
    }
    return { action: "deny" };
  });
  mainWindow.webContents.on("will-navigate", (event, url) => {
    const current = mainWindow.webContents.getURL();
    if (url !== current && (url.startsWith("http:") || url.startsWith("https:"))) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });
}

// ---------------------------------------------------------------------------
// Native application menu
// ---------------------------------------------------------------------------
function buildMenu() {
  const isMac = process.platform === "darwin";
  const template = [
    ...(isMac
      ? [{
          label: app.name,
          submenu: [
            { role: "about" },
            { type: "separator" },
            { role: "hide" },
            { role: "quit" },
          ],
        }]
      : []),
    {
      label: "File",
      submenu: [
        {
          label: "Check for Updates…",
          click: () => autoUpdater.checkForUpdatesAndNotify(),
        },
        { type: "separator" },
        isMac ? { role: "close" } : { role: "quit" },
      ],
    },
    {
      label: "View",
      submenu: [
        { role: "reload" },
        { role: "forceReload" },
        { role: "toggleDevTools" },
        { type: "separator" },
        { role: "resetZoom" },
        { role: "zoomIn" },
        { role: "zoomOut" },
        { type: "separator" },
        { role: "togglefullscreen" },
        {
          label: "Toggle Dark/Light",
          click: () => {
            nativeTheme.themeSource = nativeTheme.shouldUseDarkColors ? "light" : "dark";
          },
        },
      ],
    },
    { role: "windowMenu" },
    {
      role: "help",
      submenu: [
        {
          label: "Documentation",
          click: () => shell.openExternal("https://github.com/ryudkiss-hue/nyc_data"),
        },
        {
          label: "Report an Issue",
          click: () => shell.openExternal("https://github.com/ryudkiss-hue/nyc_data/issues"),
        },
        {
          label: "About",
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: "info",
              title: "About",
              message: "Manhattan Mission Control",
              detail: `NYC DOT Open Data Explorer & Agency Analytics\nVersion ${app.getVersion()}`,
            });
          },
        },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ---------------------------------------------------------------------------
// System tray
// ---------------------------------------------------------------------------
function buildTray() {
  const iconPath = path.join(
    __dirname,
    "build",
    process.platform === "win32" ? "icon.ico" : "icon.png"
  );
  try {
    tray = new Tray(iconPath);
  } catch {
    return; // icon missing during early dev — skip tray
  }
  tray.setToolTip("Manhattan Mission Control");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      {
        label: "Show",
        click: () => {
          if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
          } else {
            createWindow();
          }
        },
      },
      { type: "separator" },
      { label: "Quit", click: () => app.quit() },
    ])
  );
  tray.on("click", () => {
    if (mainWindow) mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show();
  });
}

// ---------------------------------------------------------------------------
// Optional Python FastAPI sidecar (off unless MMC_SIDECAR=1)
// ---------------------------------------------------------------------------
function startSidecar() {
  if (process.env.MMC_SIDECAR !== "1") return;
  const { spawn } = require("child_process");
  const python = process.env.MMC_PYTHON || "python";
  sidecar = spawn(
    python,
    ["-m", "uvicorn", "app.sidecar_api:app", "--host", "127.0.0.1", "--port", "8000"],
    { cwd: path.join(__dirname, ".."), stdio: "ignore" }
  );
  sidecar.on("error", (err) => console.error("Sidecar failed to start:", err));
}

function stopSidecar() {
  if (sidecar && !sidecar.killed) sidecar.kill();
}

// ---------------------------------------------------------------------------
// IPC — minimal, safe surface exposed via preload
// ---------------------------------------------------------------------------
ipcMain.handle("app:getVersion", () => app.getVersion());
ipcMain.handle("app:openExternal", (_e, url) => {
  if (typeof url === "string" && (url.startsWith("http:") || url.startsWith("https:"))) {
    return shell.openExternal(url);
  }
});

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });

  app.whenReady().then(() => {
    buildMenu();
    createWindow();
    buildTray();
    startSidecar();

    if (!isDev) {
      autoUpdater.checkForUpdatesAndNotify().catch(() => {});
    }

    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
  });

  app.on("before-quit", stopSidecar);
}

// ---------------------------------------------------------------------------
// Auto-updater UX
// ---------------------------------------------------------------------------
autoUpdater.on("update-downloaded", (info) => {
  if (!mainWindow) return;
  dialog
    .showMessageBox(mainWindow, {
      type: "info",
      buttons: ["Restart now", "Later"],
      title: "Update ready",
      message: `Version ${info.version} has been downloaded.`,
      detail: "Restart the app to apply the update.",
    })
    .then((res) => {
      if (res.response === 0) autoUpdater.quitAndInstall();
    });
});
