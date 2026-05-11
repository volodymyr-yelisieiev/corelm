import {
  Activity,
  Archive,
  Bot,
  Boxes,
  Braces,
  Clipboard,
  Cloud,
  Code2,
  Download,
  FileInput,
  GitBranch,
  History,
  Import,
  Layers,
  MessageSquare,
  Network,
  Play,
  Plus,
  Radio,
  RefreshCw,
  Route,
  Save,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  Terminal,
  Upload
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import type {
  ChatMessage,
  ConnectorRecord,
  LedgerMirror,
  MetricRecord,
  ReplaySnapshot,
  SessionRecord,
  StudioState,
  Workflow,
  WorkflowNode,
  WorkflowRunRecord,
  WorkflowRunResult
} from "./types";

type Mode = "console" | "flow";
type DrawerTab = "history" | "connectors" | "settings";

const defaultWorkflow: Workflow = {
  id: "demo-canonical-flow",
  name: "Canonical Core LM Flow",
  description: "Manual text through Core LM and outbound packet export.",
  schedule: { enabled: false, cron: "" },
  nodes: [
    { id: "n1", type: "manual_text_input", position: { x: 48, y: 96 }, config: { text: "project.name = Core LM Studio" } },
    { id: "n2", type: "clean_text", position: { x: 292, y: 96 }, config: {} },
    { id: "n3", type: "canonicalize", position: { x: 536, y: 96 }, config: {} },
    { id: "n4", type: "core_lm", position: { x: 780, y: 96 }, config: { format: "markdown" } },
    { id: "n5", type: "chat", position: { x: 1024, y: 96 }, config: {} },
    { id: "n6", type: "outbound_prompt", position: { x: 1268, y: 96 }, config: { target_type: "programming_agent_packet" } }
  ],
  edges: [
    { id: "e1", source: "n1", target: "n2" },
    { id: "e2", source: "n2", target: "n3" },
    { id: "e3", source: "n3", target: "n4" },
    { id: "e4", source: "n4", target: "n5" },
    { id: "e5", source: "n5", target: "n6" }
  ]
};

function compactDigest(value?: string): string {
  if (!value) {
    return "pending";
  }
  return `${value.slice(0, 10)}...${value.slice(-6)}`;
}

function tryReadNumber(value: unknown): string {
  return typeof value === "number" ? value.toFixed(3) : "0.000";
}

export default function App() {
  const [mode, setMode] = useState<Mode>("console");
  const [drawerTab, setDrawerTab] = useState<DrawerTab>("history");
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [sessionId, setSessionId] = useState("default");
  const [branch, setBranch] = useState("corelm");
  const [inputText, setInputText] = useState("project.name = Core LM Studio\nllm.role = perturbation source only");
  const [readout, setReadout] = useState("Core LM Studio ready");
  const [status, setStatus] = useState<"offline" | "online" | "busy">("offline");
  const [state, setState] = useState<StudioState | null>(null);
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [ledger, setLedger] = useState<LedgerMirror[]>([]);
  const [metrics, setMetrics] = useState<MetricRecord[]>([]);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [connectors, setConnectors] = useState<ConnectorRecord[]>([]);
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  const [replaySnapshots, setReplaySnapshots] = useState<ReplaySnapshot[]>([]);
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRunRecord[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [workflow, setWorkflow] = useState<Workflow>(defaultWorkflow);
  const [runResult, setRunResult] = useState<WorkflowRunResult | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState("n4");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [historyQuery, setHistoryQuery] = useState("");
  const [provenance, setProvenance] = useState<Record<string, unknown> | null>(null);
  const importRef = useRef<HTMLInputElement | null>(null);

  const latestMessage = chat[chat.length - 1];
  const latestMetric = metrics[metrics.length - 1]?.metric;
  const branches = state?.branches?.length ? state.branches : ["corelm"];

  const refresh = useCallback(async () => {
    try {
      const health = await api.health();
      const [
        nextChat,
        nextLedger,
        nextMetrics,
        nextWorkflows,
        nextConnectors,
        nextSettings,
        nextReplaySnapshots,
        nextWorkflowRuns,
        nextState,
        nextSessions
      ] = await Promise.all([
        api.chat(sessionId),
        api.ledger(sessionId),
        api.metrics(sessionId),
        api.workflows(),
        api.connectors(),
        api.settings(),
        api.replaySnapshots(sessionId),
        api.workflowRuns(sessionId),
        api.state(sessionId),
        api.sessions()
      ].map((request) => request.then((value) => ({ status: "fulfilled" as const, value })).catch(() => ({ status: "rejected" as const }))));
      const apply = <T,>(result: { status: "fulfilled"; value: T } | { status: "rejected" }, setter: (value: T) => void) => {
        if (result.status === "fulfilled") {
          setter(result.value);
        }
      };
      const stateResult = nextState as { status: "fulfilled"; value: StudioState } | { status: "rejected" };
      const sessionsResult = nextSessions as { status: "fulfilled"; value: SessionRecord[] } | { status: "rejected" };
      const workflowsResult = nextWorkflows as { status: "fulfilled"; value: Workflow[] } | { status: "rejected" };
      setStatus("online");
      setState(stateResult.status === "fulfilled" ? stateResult.value : health.state);
      apply(nextChat as { status: "fulfilled"; value: ChatMessage[] } | { status: "rejected" }, setChat);
      apply(nextLedger as { status: "fulfilled"; value: LedgerMirror[] } | { status: "rejected" }, setLedger);
      apply(nextMetrics as { status: "fulfilled"; value: MetricRecord[] } | { status: "rejected" }, setMetrics);
      apply(nextConnectors as { status: "fulfilled"; value: ConnectorRecord[] } | { status: "rejected" }, setConnectors);
      apply(nextSettings as { status: "fulfilled"; value: Record<string, unknown> } | { status: "rejected" }, setSettings);
      apply(nextReplaySnapshots as { status: "fulfilled"; value: ReplaySnapshot[] } | { status: "rejected" }, setReplaySnapshots);
      apply(nextWorkflowRuns as { status: "fulfilled"; value: WorkflowRunRecord[] } | { status: "rejected" }, setWorkflowRuns);
      if (sessionsResult.status === "fulfilled") {
        setSessions(Array.isArray(sessionsResult.value) ? sessionsResult.value : []);
      }
      if (workflowsResult.status === "fulfilled") {
        setWorkflows(workflowsResult.value);
        if (workflowsResult.value.length > 0 && workflow.id === defaultWorkflow.id) {
          setWorkflow(workflowsResult.value[0]);
        }
      }
    } catch {
      setStatus("offline");
    }
  }, [sessionId, workflow.id]);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((open) => !open);
      }
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        void ingestText();
      }
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === "f") {
        event.preventDefault();
        setMode("flow");
      }
      if (event.key === "Escape") {
        setPaletteOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  const filteredChat = useMemo(() => {
    if (!historyQuery.trim()) {
      return chat;
    }
    const query = historyQuery.toLowerCase();
    return chat.filter((message) => message.content.toLowerCase().includes(query) || message.origin.toLowerCase().includes(query));
  }, [chat, historyQuery]);

  async function ingestText() {
    if (!inputText.trim()) {
      return;
    }
    setStatus("busy");
    setReadout("ingesting canonical candidate...");
    try {
      const result = await api.ingest({
        session_id: sessionId,
        branch,
        text: inputText,
        format: "markdown",
        source: {
          source_id: "console-manual",
          source_type: "manual_text",
          trust_level: "medium",
          branch
        },
        compression: {
          steps: ["sanitize", "clean", "dedupe", "canonicalize", "schema_extract", "hash_compress", "contradiction_tag"],
          allow_raw_commit: true
        }
      });
      setReadout(`ledger ${String((result.ledger_entry as Record<string, unknown>)?.entry_id ?? "committed")} | ${compactDigest(String(result.digest ?? ""))}`);
      await refresh();
    } catch (error) {
      setReadout(error instanceof Error ? error.message : "ingest failed");
      setStatus("online");
    }
  }

  async function previewCompression() {
    const canonical = inputText
      .replace(/\r\n/g, "\n")
      .split("\n")
      .map((line) => line.trim())
      .filter((line, index, lines) => line.length === 0 || lines.indexOf(line) === index)
      .join("\n")
      .trim();
    setReadout(canonical || "empty canonical preview");
  }

  async function routeLatest() {
    if (!latestMessage) {
      setReadout("no chat message to route");
      return;
    }
    setStatus("busy");
    const receipt = await api.routeChat(latestMessage.id, sessionId, "engineering_task_packet");
    setReadout(`routed ${String(receipt.receipt_id ?? "packet")} -> ${String(receipt.status ?? "prepared")}`);
    await refresh();
  }

  async function loadReplay() {
    const replay = await api.replay(sessionId);
    setReadout(`replay ${replay.ok ? "consistent" : "attention"} | ${compactDigest(String(replay.expected_digest ?? ""))}`);
  }

  async function inspectProvenance() {
    const result = await api.provenance(sessionId, branch, "project", "name");
    setProvenance(result);
    setDrawerOpen(true);
    setDrawerTab("history");
    setReadout(String(result.provenance ?? "UNKNOWN"));
  }

  async function promoteLatest() {
    if (!latestMessage) {
      return;
    }
    await api.promoteChat(latestMessage.id, sessionId, branch);
    setReadout("chat message promoted through Core LM rules");
    await refresh();
  }

  async function runCurrentWorkflow() {
    setStatus("busy");
    const result = await api.runWorkflow(workflow, sessionId, branch, { text: inputText });
    setRunResult(result);
    setReadout(result.status === "ok" ? `workflow ${workflow.name} complete` : `workflow ${workflow.name} needs attention`);
    await refresh();
  }

  async function saveCurrentWorkflow() {
    const saved = await api.saveWorkflow(workflow);
    setWorkflow(saved);
    setReadout(`saved ${saved.name}`);
    await refresh();
  }

  async function cloneCurrentWorkflow() {
    const cloned = await api.cloneWorkflow(workflow.id);
    setWorkflow(cloned);
    setReadout(`cloned ${cloned.name}`);
    await refresh();
  }

  function exportWorkflow() {
    const blob = new Blob([JSON.stringify(workflow, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${workflow.id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function onImportWorkflow(file: File) {
    const text = await file.text();
    const imported = JSON.parse(text) as Workflow;
    setWorkflow(imported);
    await api.saveWorkflow(imported);
    setReadout(`imported ${imported.name}`);
    await refresh();
  }

  async function handleDrop(event: React.DragEvent) {
    event.preventDefault();
    const file = event.dataTransfer.files.item(0);
    if (!file) {
      return;
    }
    const text = await file.text();
    setInputText(text);
    setStatus("busy");
    setReadout(`ingesting ${file.name}...`);
    await api.ingest({
      session_id: sessionId,
      branch,
      text,
      format: "markdown",
      source: {
        source_id: file.name,
        source_type: "file_drop",
        file_name: file.name,
        file_size: file.size,
        trust_level: "medium",
        branch
      },
      compression: {
        steps: ["sanitize", "clean", "dedupe", "canonicalize", "schema_extract", "hash_compress", "contradiction_tag"],
        allow_raw_commit: true
      }
    });
    setReadout(`ingested ${file.name}`);
    await refresh();
  }

  async function createSession() {
    const next = await api.createSession(`Studio Session ${sessions.length + 1}`);
    setSessionId(next.id);
    setBranch(next.current_branch || "corelm");
    setReadout(`created session ${next.id}`);
    await refresh();
  }

  async function runConnectorIntoCore(connectorType: string, config: Record<string, unknown>) {
    setStatus("busy");
    setReadout(`running ${connectorType} through Core LM...`);
    try {
      const result = await api.runConnectorIngest({
        connector_type: connectorType,
        session_id: sessionId,
        branch,
        config,
        format: "markdown",
        compression: {
          steps: ["sanitize", "clean", "dedupe", "canonicalize", "schema_extract", "hash_compress", "contradiction_tag"],
          allow_raw_commit: true
        }
      });
      const ingest = result.ingest;
      setReadout(`connector ${connectorType} committed ${String(ingest.event_id ?? "event")} | ${compactDigest(String(ingest.digest ?? ""))}`);
      await refresh();
    } catch (error) {
      setReadout(error instanceof Error ? error.message : "connector run failed");
      setStatus("online");
    }
  }

  async function saveConnector(connector: ConnectorRecord) {
    await api.saveConnector(connector);
    setReadout(`saved connector ${connector.name}`);
    await refresh();
  }

  async function deleteConnector(connectorId: string) {
    await api.deleteConnector(connectorId);
    setReadout(`deleted connector ${connectorId}`);
    await refresh();
  }

  async function updateStudioSettings(patch: Record<string, unknown>) {
    const next = await api.updateSettings(patch);
    setSettings(next);
    setReadout("settings persisted");
  }

  const selectedNode = workflow.nodes.find((node) => node.id === selectedNodeId) ?? workflow.nodes[0];

  return (
    <main className="app-shell" onDragOver={(event) => event.preventDefault()} onDrop={handleDrop}>
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">
            <Sparkles size={22} />
          </div>
          <div>
            <h1>Core LM Studio</h1>
            <span>{api.serviceUrl}</span>
          </div>
        </div>
        <nav className="mode-tabs" aria-label="Primary modes">
          <button className={mode === "console" ? "active" : ""} onClick={() => setMode("console")}>
            <Terminal size={18} /> Console
          </button>
          <button className={mode === "flow" ? "active" : ""} onClick={() => setMode("flow")}>
            <Network size={18} /> Flow Studio
          </button>
        </nav>
        <div className="top-controls">
          <label>
            <GitBranch size={16} />
            <select value={branch} onChange={(event) => setBranch(event.target.value)}>
              {branches.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label>
            <Archive size={16} />
            <select value={sessionId} onChange={(event) => setSessionId(event.target.value)}>
              {sessions.length === 0 && <option value="default">default</option>}
              {sessions.map((session) => (
                <option key={session.id} value={session.id}>
                  {session.id}
                </option>
              ))}
            </select>
          </label>
          <button className="icon-button" title="New session" onClick={() => void createSession()}>
            <Plus size={18} />
          </button>
          <button className="icon-button" title="Command palette" onClick={() => setPaletteOpen(true)}>
            <Search size={18} />
          </button>
          <span className={`status-pill ${status}`}>
            <Radio size={15} /> {status}
          </span>
        </div>
      </header>

      {paletteOpen && (
        <div className="palette" role="dialog" aria-label="Command palette">
          <div className="palette-inner">
            <button onClick={() => void ingestText()}>
              <Play size={17} /> Run Core LM
            </button>
            <button onClick={() => setMode("flow")}>
              <Network size={17} /> Flow Studio
            </button>
            <button onClick={() => void routeLatest()}>
              <Send size={17} /> Route latest
            </button>
            <button onClick={() => void loadReplay()}>
              <RefreshCw size={17} /> Replay session
            </button>
          </div>
        </div>
      )}

      {mode === "console" ? (
        <section className="console-layout" data-testid="console-mode">
          <section className="console-main">
            <div className="readout-panel">
              <span className="readout-kicker">canonical response</span>
              <p>{readout}</p>
              <div className="readout-meta">
                <span>digest {compactDigest(state?.digest)}</span>
                <span>ledger {state?.stats?.ledger_entries ?? 0}</span>
                <span>facts {state?.stats?.current_facts ?? 0}</span>
              </div>
            </div>

            <div className="core-center">
              <div className={`core-orb ${state?.health === "healthy" ? "healthy" : "attention"}`}>
                <Activity size={36} />
                <strong>{tryReadNumber(latestMetric?.state_norm)}</strong>
                <span>state norm</span>
              </div>
              <div className="core-stats">
                <span>branch {branch}</span>
                <span>replay {state?.replay?.ok ? "consistent" : "pending"}</span>
                <span>drift {tryReadNumber(latestMetric?.drift)}</span>
                <span>energy {tryReadNumber(latestMetric?.energy)}</span>
              </div>
            </div>

            <div className="input-strip">
              <textarea value={inputText} onChange={(event) => setInputText(event.target.value)} aria-label="Core LM input" />
              <div className="format-stack">
                <button onClick={() => setInputText("project.name = Core LM Studio\npipeline.order = source -> compression -> core -> chat -> outbound")}>
                  <Plus size={18} /> Demo
                </button>
                <button onClick={() => setInputText("")}>
                  <Clipboard size={18} /> Clear
                </button>
              </div>
            </div>

            <div className="action-pad">
              <ActionButton icon={<FileInput size={25} />} label="Ingest" onClick={() => void ingestText()} />
              <ActionButton icon={<Boxes size={25} />} label="Compress" onClick={() => void previewCompression()} />
              <ActionButton icon={<Bot size={25} />} label="Core LM" onClick={() => void ingestText()} primary />
              <ActionButton icon={<MessageSquare size={25} />} label="Chat" onClick={() => void refresh()} />
              <ActionButton icon={<Send size={25} />} label="Route" onClick={() => void routeLatest()} />
              <ActionButton icon={<Layers size={25} />} label="Ledger" onClick={() => setDrawerTab("history")} />
              <ActionButton icon={<RefreshCw size={25} />} label="Replay" onClick={() => void loadReplay()} />
              <ActionButton icon={<ShieldCheck size={25} />} label="Provenance" onClick={() => void inspectProvenance()} />
            </div>
          </section>

          {drawerOpen && (
            <aside className="side-drawer">
              <div className="drawer-tabs">
                <button className={drawerTab === "history" ? "active" : ""} onClick={() => setDrawerTab("history")}>
                  <History size={16} /> History
                </button>
                <button className={drawerTab === "connectors" ? "active" : ""} onClick={() => setDrawerTab("connectors")}>
                  <Route size={16} /> Connectors
                </button>
                <button className={drawerTab === "settings" ? "active" : ""} onClick={() => setDrawerTab("settings")}>
                  <Settings size={16} /> Settings
                </button>
              </div>
              {drawerTab === "history" && (
                <HistoryPanel
                  query={historyQuery}
                  setQuery={setHistoryQuery}
                  chat={filteredChat}
                  ledger={ledger}
                  provenance={provenance}
                  replaySnapshots={replaySnapshots}
                  workflowRuns={workflowRuns}
                  onRoute={routeLatest}
                  onPromote={promoteLatest}
                />
              )}
              {drawerTab === "connectors" && (
                <ConnectorPanel
                  connectors={connectors}
                  branch={branch}
                  onRun={runConnectorIntoCore}
                  onSave={saveConnector}
                  onDelete={deleteConnector}
                />
              )}
              {drawerTab === "settings" && <SettingsPanel state={state} settings={settings} onUpdate={updateStudioSettings} />}
            </aside>
          )}
        </section>
      ) : (
        <FlowStudio
          workflow={workflow}
          setWorkflow={setWorkflow}
          workflows={workflows}
          setSelectedNodeId={setSelectedNodeId}
          selectedNode={selectedNode}
          runResult={runResult}
          onRun={runCurrentWorkflow}
          onSave={saveCurrentWorkflow}
          onClone={cloneCurrentWorkflow}
          onExport={exportWorkflow}
          onImport={() => importRef.current?.click()}
        />
      )}

      <input
        ref={importRef}
        className="hidden-input"
        type="file"
        accept="application/json,.json"
        onChange={(event) => {
          const file = event.currentTarget.files?.item(0);
          if (file) {
            void onImportWorkflow(file);
          }
        }}
      />
    </main>
  );
}

function ActionButton({ icon, label, onClick, primary = false }: { icon: React.ReactNode; label: string; onClick: () => void; primary?: boolean }) {
  return (
    <button className={`action-button ${primary ? "primary" : ""}`} onClick={onClick}>
      {icon}
      <span>{label}</span>
    </button>
  );
}

function HistoryPanel({
  query,
  setQuery,
  chat,
  ledger,
  provenance,
  replaySnapshots,
  workflowRuns,
  onRoute,
  onPromote
}: {
  query: string;
  setQuery: (value: string) => void;
  chat: ChatMessage[];
  ledger: LedgerMirror[];
  provenance: Record<string, unknown> | null;
  replaySnapshots: ReplaySnapshot[];
  workflowRuns: WorkflowRunRecord[];
  onRoute: () => Promise<void>;
  onPromote: () => Promise<void>;
}) {
  return (
    <div className="drawer-body">
      <label className="search-field">
        <Search size={16} />
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search history" />
      </label>
      <div className="inline-actions">
        <button onClick={() => void onRoute()}>
          <Send size={16} /> Send to...
        </button>
        <button onClick={() => void onPromote()}>
          <Upload size={16} /> Promote
        </button>
      </div>
      <div className="chat-list">
        {chat.map((message) => (
          <article key={message.id} className="chat-item">
            <div>
              <span>{message.origin}</span>
              <span>{message.branch}</span>
              <span>{message.format}</span>
            </div>
            <p>{message.content}</p>
          </article>
        ))}
      </div>
      <h2>Ledger</h2>
      <div className="ledger-list">
        {ledger.slice(-6).map((entry) => (
          <article key={`${entry.session_id}-${entry.entry_id}`} className="ledger-item">
            <strong>{entry.entry_id}</strong>
            <span>{entry.branch}</span>
            <p>{entry.raw_text}</p>
          </article>
        ))}
      </div>
      {provenance && (
        <div className="provenance-box">
          <h2>Provenance</h2>
          <pre>{JSON.stringify(provenance, null, 2)}</pre>
        </div>
      )}
      <h2>Replay</h2>
      <div className="ledger-list">
        {replaySnapshots.slice(-4).map((snapshot) => (
          <article key={snapshot.id} className="ledger-item">
            <strong>{snapshot.ok ? "consistent" : "attention"}</strong>
            <span>{compactDigest(snapshot.digest)}</span>
            <p>{snapshot.created_at}</p>
          </article>
        ))}
      </div>
      <h2>Workflow Runs</h2>
      <div className="trace-list">
        {workflowRuns.slice(-4).map((run) => (
          <article key={run.id} className={`trace-item ${run.status}`}>
            <strong>{run.workflow_id}</strong>
            <span>{run.created_at}</span>
            <code>{run.status}</code>
          </article>
        ))}
      </div>
    </div>
  );
}

function ConnectorPanel({
  connectors,
  branch,
  onRun,
  onSave,
  onDelete
}: {
  connectors: ConnectorRecord[];
  branch: string;
  onRun: (connectorType: string, config: Record<string, unknown>) => Promise<void>;
  onSave: (connector: ConnectorRecord) => Promise<void>;
  onDelete: (connectorId: string) => Promise<void>;
}) {
  const inbound = [
    { type: "manual_text", label: "Manual text" },
    { type: "openai_compatible_llm", label: "OpenAI-compatible" },
    { type: "ollama_local_model", label: "Ollama/local" },
    { type: "file_input", label: "File input" },
    { type: "folder_watcher", label: "Folder watcher" },
    { type: "generic_web_api_fetch", label: "Web/API fetch" },
    { type: "generic_rest_input", label: "REST input" },
    { type: "clipboard_input", label: "Clipboard" },
    { type: "shell_cli_capture", label: "Shell capture" }
  ];
  const outbound = ["HTTP/REST", "OpenAI-compatible", "Local model", "File export", "Clipboard", "Shell handoff", "Programming packet"];
  const [connectorType, setConnectorType] = useState("openai_compatible_llm");
  const [prompt, setPrompt] = useState("connector.demo = deterministic mock ingress");
  const [connectorName, setConnectorName] = useState("Mock ingress");

  function runConfigFor(type: string): Record<string, unknown> {
    if (type === "file_input") {
      return { path: prompt, content_type: "text/plain", branch };
    }
    if (type === "folder_watcher") {
      return { path: prompt, pattern: "*", branch };
    }
    if (type === "generic_web_api_fetch" || type === "generic_rest_input") {
      return { url: prompt, method: "GET", timeout: 30, branch };
    }
    if (type === "manual_text" || type === "clipboard_input") {
      return { text: prompt, mock: true, branch };
    }
    return { prompt, text: prompt, mock: true, branch };
  }

  const runConfig = runConfigFor(connectorType);

  function connectorDraft(): ConnectorRecord {
    const id = connectorName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "connector";
    return {
      id,
      name: connectorName,
      direction: "inbound",
      type: connectorType,
      config: runConfig,
      secret_refs: connectorType.includes("openai") ? ["OPENAI_API_KEY"] : [],
      enabled: true
    };
  }

  return (
    <div className="drawer-body connector-grid">
      <section>
        <h2>Inbound</h2>
        <label className="stacked-field">
          Type
          <select value={connectorType} onChange={(event) => setConnectorType(event.target.value)}>
            {inbound.map((item) => (
              <option key={item.type} value={item.type}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="stacked-field">
          Name
          <input value={connectorName} onChange={(event) => setConnectorName(event.target.value)} />
        </label>
        <label className="stacked-field">
          Payload
          <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} />
        </label>
        <div className="inline-actions">
          <button onClick={() => void onRun(connectorType, runConfig)}>
            <Play size={16} /> Run through Core
          </button>
          <button onClick={() => void onSave(connectorDraft())}>
            <Save size={16} /> Save
          </button>
        </div>
      </section>
      <section>
        <h2>Outbound</h2>
        {outbound.map((item) => (
          <span key={item} className="connector-pill">
            <Send size={15} /> {item}
          </span>
        ))}
      </section>
      <section>
        <h2>Saved</h2>
        {connectors.length === 0 && <span className="connector-pill">No saved connectors</span>}
        {connectors.map((connector) => (
          <article key={connector.id} className="connector-record">
            <div>
              <strong>{connector.name}</strong>
              <span>{connector.type}</span>
            </div>
            <button onClick={() => void onRun(connector.type, connector.config)}>
              <Play size={15} /> Run
            </button>
            <button onClick={() => void onDelete(connector.id)}>
              <Archive size={15} /> Delete
            </button>
          </article>
        ))}
      </section>
    </div>
  );
}

function SettingsPanel({
  state,
  settings,
  onUpdate
}: {
  state: StudioState | null;
  settings: Record<string, unknown>;
  onUpdate: (patch: Record<string, unknown>) => Promise<void>;
}) {
  return (
    <div className="drawer-body settings-grid">
      <section>
        <h2>State</h2>
        <span>health {state?.health ?? "offline"}</span>
        <span>digest {compactDigest(state?.digest)}</span>
        <span>invariants {state?.stats?.invariant_violations ?? 0}</span>
      </section>
      <section>
        <h2>Security</h2>
        <span>secrets redacted</span>
        <span>offline-capable</span>
        <span>SQLite local store</span>
      </section>
      <section>
        <h2>Preferences</h2>
        <span>console density {String(settings.console_density ?? "comfortable")}</span>
        <button onClick={() => void onUpdate({ console_density: settings.console_density === "compact" ? "comfortable" : "compact" })}>
          <Settings size={16} /> Toggle density
        </button>
      </section>
    </div>
  );
}

function FlowStudio({
  workflow,
  setWorkflow,
  workflows,
  setSelectedNodeId,
  selectedNode,
  runResult,
  onRun,
  onSave,
  onClone,
  onExport,
  onImport
}: {
  workflow: Workflow;
  setWorkflow: (workflow: Workflow) => void;
  workflows: Workflow[];
  setSelectedNodeId: (id: string) => void;
  selectedNode: WorkflowNode;
  runResult: WorkflowRunResult | null;
  onRun: () => Promise<void>;
  onSave: () => Promise<void>;
  onClone: () => Promise<void>;
  onExport: () => void;
  onImport: () => void;
}) {
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const [dragging, setDragging] = useState<{ id: string; offsetX: number; offsetY: number } | null>(null);

  function updateNode(nodeId: string, patch: Partial<WorkflowNode>) {
    setWorkflow({
      ...workflow,
      nodes: workflow.nodes.map((node) => (node.id === nodeId ? { ...node, ...patch } : node))
    });
  }

  function addNode(type: string) {
    const id = `n${Date.now().toString(36)}`;
    const base = selectedNode?.position ?? { x: 48, y: 96 };
    const node: WorkflowNode = {
      id,
      type,
      position: { x: base.x + 230, y: base.y + (workflow.nodes.length % 3) * 30 },
      config: type === "core_lm" ? { format: "markdown" } : type === "outbound_prompt" ? { target_type: "programming_agent_packet" } : {}
    };
    const edge = selectedNode ? { id: `e-${selectedNode.id}-${id}`, source: selectedNode.id, target: id } : null;
    setWorkflow({
      ...workflow,
      nodes: [...workflow.nodes, node],
      edges: edge ? [...workflow.edges, edge] : workflow.edges
    });
    setSelectedNodeId(id);
  }

  function deleteSelectedNode() {
    if (!selectedNode || workflow.nodes.length <= 1) {
      return;
    }
    const remaining = workflow.nodes.filter((node) => node.id !== selectedNode.id);
    setWorkflow({
      ...workflow,
      nodes: remaining,
      edges: workflow.edges.filter((edge) => edge.source !== selectedNode.id && edge.target !== selectedNode.id)
    });
    setSelectedNodeId(remaining[0].id);
  }

  function pointerMove(event: React.PointerEvent) {
    if (!dragging || !canvasRef.current) {
      return;
    }
    const rect = canvasRef.current.getBoundingClientRect();
    updateNode(dragging.id, {
      position: {
        x: Math.max(0, event.clientX - rect.left - dragging.offsetX),
        y: Math.max(0, event.clientY - rect.top - dragging.offsetY)
      }
    });
  }

  function nodeCenter(id: string) {
    const node = workflow.nodes.find((item) => item.id === id);
    return node ? { x: node.position.x + 86, y: node.position.y + 34 } : { x: 0, y: 0 };
  }

  return (
    <section className="flow-layout" data-testid="flow-mode">
      <header className="flow-toolbar">
        <div>
          <h2>{workflow.name}</h2>
          <span>{workflow.id}</span>
        </div>
        <select
          value={workflow.id}
          onChange={(event) => {
            const next = workflows.find((item) => item.id === event.target.value);
            if (next) {
              setWorkflow(next);
            }
          }}
        >
          {[workflow, ...workflows.filter((item) => item.id !== workflow.id)].map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
        <button onClick={() => void onRun()}>
          <Play size={17} /> Test Run
        </button>
        <button onClick={() => void onSave()}>
          <Save size={17} /> Save
        </button>
        <button onClick={() => void onClone()}>
          <Plus size={17} /> Clone
        </button>
        <button onClick={onExport}>
          <Download size={17} /> Export
        </button>
        <button onClick={onImport}>
          <Import size={17} /> Import
        </button>
        <button onClick={() => addNode("manual_text_input")}>
          <FileInput size={17} /> Input
        </button>
        <button onClick={() => addNode("clean_text")}>
          <Boxes size={17} /> Prep
        </button>
        <button onClick={() => addNode("core_lm")}>
          <Bot size={17} /> Core
        </button>
        <button onClick={() => addNode("outbound_prompt")}>
          <Send size={17} /> Out
        </button>
        <button onClick={deleteSelectedNode}>
          <Archive size={17} /> Delete
        </button>
      </header>

      <div className="flow-workspace">
        <div
          ref={canvasRef}
          className="workflow-canvas"
          onPointerMove={pointerMove}
          onPointerUp={() => setDragging(null)}
          onPointerLeave={() => setDragging(null)}
        >
          <svg className="edge-layer">
            {workflow.edges.map((edge) => {
              const source = nodeCenter(edge.source);
              const target = nodeCenter(edge.target);
              const control = Math.max(80, Math.abs(target.x - source.x) / 2);
              return (
                <path
                  key={edge.id}
                  d={`M ${source.x} ${source.y} C ${source.x + control} ${source.y}, ${target.x - control} ${target.y}, ${target.x} ${target.y}`}
                />
              );
            })}
          </svg>
          {workflow.nodes.map((node) => (
            <button
              key={node.id}
              className={`flow-node ${selectedNode.id === node.id ? "selected" : ""}`}
              style={{ transform: `translate(${node.position.x}px, ${node.position.y}px)` }}
              onPointerDown={(event) => {
                setSelectedNodeId(node.id);
                const rect = (event.currentTarget as HTMLButtonElement).getBoundingClientRect();
                setDragging({ id: node.id, offsetX: event.clientX - rect.left, offsetY: event.clientY - rect.top });
              }}
            >
              <span>{iconForNode(node.type)}</span>
              <strong>{node.type}</strong>
              <small>{node.id}</small>
            </button>
          ))}
        </div>
        <aside className="inspector">
          <h2>Inspector</h2>
          <label>
            Type
            <input value={selectedNode.type} onChange={(event) => updateNode(selectedNode.id, { type: event.target.value })} />
          </label>
          <label>
            Config
            <textarea
              value={JSON.stringify(selectedNode.config, null, 2)}
              onChange={(event) => {
                try {
                  updateNode(selectedNode.id, { config: JSON.parse(event.target.value) as Record<string, unknown> });
                } catch {
                  updateNode(selectedNode.id, { config: { raw: event.target.value } });
                }
              }}
            />
          </label>
          <h2>Trace</h2>
          <div className="trace-list">
            {(runResult?.trace ?? []).map((item) => (
              <article key={String(item.node_id)} className={`trace-item ${String(item.status)}`}>
                <strong>{String(item.node_id)}</strong>
                <span>{String(item.type)}</span>
                <code>{String(item.status)}</code>
              </article>
            ))}
          </div>
        </aside>
      </div>
    </section>
  );
}

function iconForNode(type: string) {
  if (type.includes("core")) {
    return <Bot size={18} />;
  }
  if (type.includes("chat")) {
    return <MessageSquare size={18} />;
  }
  if (type.includes("outbound")) {
    return <Send size={18} />;
  }
  if (type.includes("format")) {
    return <Braces size={18} />;
  }
  if (type.includes("input")) {
    return <FileInput size={18} />;
  }
  return <Code2 size={18} />;
}
