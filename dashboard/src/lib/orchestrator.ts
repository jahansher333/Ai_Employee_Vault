import { spawn, ChildProcess } from "child_process";
import path from "path";
import { VAULT, appendAuditLog } from "./vault";

let orchestratorProc: ChildProcess | null = null;

export function getOrchestratorState() {
  const running = orchestratorProc !== null && orchestratorProc.exitCode === null;
  return {
    running,
    pid: running ? orchestratorProc!.pid : null,
  };
}

export function startOrchestrator() {
  if (orchestratorProc && orchestratorProc.exitCode === null) {
    return { success: true, message: "Orchestrator already running", pid: orchestratorProc.pid };
  }

  try {
    const scriptPath = path.join(VAULT, "scripts", "orchestrator.py");
    orchestratorProc = spawn("python", [scriptPath, "--auto-restart"], {
      cwd: VAULT,
      stdio: "ignore",
      detached: false,
    });

    const pid = orchestratorProc.pid;

    orchestratorProc.on("exit", () => {
      orchestratorProc = null;
    });

    appendAuditLog("orchestrator_start", "dashboard", String(pid), "success");
    return { success: true, message: "Orchestrator started", pid };
  } catch (err) {
    return { success: false, error: String(err) };
  }
}

export function stopOrchestrator() {
  if (!orchestratorProc || orchestratorProc.exitCode !== null) {
    orchestratorProc = null;
    return { success: true, message: "Orchestrator not running" };
  }

  try {
    const pid = orchestratorProc.pid;
    orchestratorProc.kill("SIGTERM");
    orchestratorProc = null;
    appendAuditLog("orchestrator_stop", "dashboard", String(pid), "success");
    return { success: true, message: "Orchestrator stopped" };
  } catch (err) {
    return { success: false, error: String(err) };
  }
}
