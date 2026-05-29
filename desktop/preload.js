/**
 * Preload — exposes a minimal, audited API to the renderer over a secure
 * contextBridge. The SPA runs with contextIsolation enabled and no direct
 * Node access; anything it needs from the OS must go through here.
 */

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("missionControl", {
  /** App version string (e.g. "3.0.0"). */
  getVersion: () => ipcRenderer.invoke("app:getVersion"),
  /** Open an http(s) URL in the system browser. */
  openExternal: (url) => ipcRenderer.invoke("app:openExternal", url),
  /** True so the SPA can detect it is running inside the desktop shell. */
  isDesktop: true,
  platform: process.platform,
});
