import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("whispr", {
  toggle: () => ipcRenderer.send("toggle"),
  onStatus: (callback: (status: { state: string; detail: string }) => void) => {
    ipcRenderer.on("status", (_event, status) => callback(status));
  },
});
