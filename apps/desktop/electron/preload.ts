import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("corelmStudio", {
  serviceUrl: "http://127.0.0.1:8765"
});
