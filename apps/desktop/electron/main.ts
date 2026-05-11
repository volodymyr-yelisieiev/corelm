import { app, BrowserWindow, ipcMain } from "electron";
import path from "node:path";
import http from "node:http";
import fs from "node:fs";
import { ChildProcessWithoutNullStreams, spawn } from "node:child_process";

let mainWindow: BrowserWindow | null = null;
let serviceProcess: ChildProcessWithoutNullStreams | null = null;

const serviceUrl = "http://127.0.0.1:8765";

function repoRoot(): string {
  if (process.env.CORELM_STUDIO_REPO_ROOT) {
    return process.env.CORELM_STUDIO_REPO_ROOT;
  }
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "corelm_service");
  }
  return path.resolve(__dirname, "../../..");
}

function pythonExecutable(): string {
  if (process.env.PYTHON) {
    return process.env.PYTHON;
  }
  const root = repoRoot();
  const bundledPython = path.join(root, "python", "python.exe");
  if (app.isPackaged && process.platform === "win32" && fs.existsSync(bundledPython)) {
    return bundledPython;
  }
  const localPython = process.platform === "win32"
    ? path.join(root, ".venv", "Scripts", "python.exe")
    : path.join(root, ".venv", "bin", "python");
  if (fs.existsSync(localPython)) {
    return localPython;
  }
  return process.platform === "win32" ? "python" : "python3";
}

function waitForHealth(timeoutMs = 20000): Promise<void> {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const check = () => {
      const request = http.get(`${serviceUrl}/api/health`, (response) => {
        response.resume();
        if (response.statusCode && response.statusCode >= 200 && response.statusCode < 300) {
          resolve();
          return;
        }
        retry();
      });
      request.on("error", retry);
      request.setTimeout(1000, () => {
        request.destroy();
        retry();
      });
    };
    const retry = () => {
      if (Date.now() - started > timeoutMs) {
        reject(new Error("Core LM sidecar did not become healthy in time"));
        return;
      }
      setTimeout(check, 400);
    };
    check();
  });
}

async function isServiceHealthy(): Promise<boolean> {
  try {
    await waitForHealth(1200);
    return true;
  } catch {
    return false;
  }
}

async function startService(): Promise<void> {
  if (serviceProcess) {
    return;
  }
  if (await isServiceHealthy()) {
    return;
  }
  const env = {
    ...process.env,
    PYTHONPATH: repoRoot(),
    CORELM_STUDIO_HOST: "127.0.0.1",
    CORELM_STUDIO_PORT: "8765"
  };
  const override = process.env.CORELM_STUDIO_SERVICE_CMD;
  if (override) {
    serviceProcess = spawn(override, {
      cwd: repoRoot(),
      env,
      shell: true,
      stdio: "pipe"
    }) as ChildProcessWithoutNullStreams;
  } else {
    const python = pythonExecutable();
    serviceProcess = spawn(python, ["-m", "services.core_service.corelm_studio"], {
      cwd: repoRoot(),
      env,
      shell: process.platform === "win32",
      stdio: "pipe"
    });
  }
  serviceProcess.stdout.on("data", (data) => {
    console.log(`[corelm-service] ${data.toString().trim()}`);
  });
  serviceProcess.stderr.on("data", (data) => {
    console.error(`[corelm-service] ${data.toString().trim()}`);
  });
  serviceProcess.on("error", (error) => {
    console.error(`[corelm-service] failed to start: ${error.message}`);
    serviceProcess = null;
  });
  serviceProcess.on("exit", () => {
    serviceProcess = null;
  });
}

function stopService(): void {
  if (!serviceProcess) {
    return;
  }
  serviceProcess.kill();
  serviceProcess = null;
}

async function createWindow(): Promise<void> {
  await startService();
  await waitForHealth().catch((error) => {
    console.error(error);
  });
  mainWindow = new BrowserWindow({
    width: 1420,
    height: 940,
    minWidth: 1120,
    minHeight: 760,
    backgroundColor: "#0b0d10",
    title: "Core LM Studio",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  const devUrl = process.env.ELECTRON_RENDERER_URL || "http://127.0.0.1:5173";
  if (!app.isPackaged) {
    await mainWindow.loadURL(devUrl);
  } else {
    await mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }
}

app.whenReady().then(() => {
  ipcMain.handle("corelm:service-url", () => serviceUrl);
  void createWindow().catch((error) => {
    console.error(`[corelm-studio] failed to create window: ${error instanceof Error ? error.message : String(error)}`);
    app.quit();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    stopService();
    app.quit();
  }
});

app.on("before-quit", () => {
  stopService();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    void createWindow().catch((error) => {
      console.error(`[corelm-studio] failed to recreate window: ${error instanceof Error ? error.message : String(error)}`);
    });
  }
});
