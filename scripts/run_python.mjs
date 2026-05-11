import { spawn } from "node:child_process";

const args = process.argv.slice(2);
const localPython = process.platform === "win32" ? ".venv\\Scripts\\python.exe" : ".venv/bin/python";
const candidates = [process.env.PYTHON, localPython, "python3", "python", process.platform === "win32" ? "py" : undefined].filter(Boolean);

function run(index) {
  if (index >= candidates.length) {
    console.error("No Python interpreter found. Set PYTHON to a Python 3.11+ executable.");
    process.exit(127);
  }
  const command = candidates[index];
  const commandArgs = command === "py" ? ["-3", ...args] : args;
  const child = spawn(command, commandArgs, {
    cwd: process.cwd(),
    env: { ...process.env, PYTHONPATH: process.env.PYTHONPATH || "." },
    stdio: "inherit",
    shell: false
  });
  child.on("error", () => run(index + 1));
  child.on("exit", (code) => {
    if (code === 127 && index + 1 < candidates.length) {
      run(index + 1);
      return;
    }
    process.exit(code ?? 1);
  });
}

run(0);
