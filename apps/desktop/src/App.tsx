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
import { CompressionPanel } from "./CompressionPanel";
import { defaultOllamaConfig, defaultWorkflow } from "./defaults";
import type {
  BenchmarkProfile,
  BenchmarkRun,
  ChatMessage,
  CompressionPreview,
  ConnectorRecord,
  DirectRuntimeAdapterInfo,
  LedgerMirror,
  LocalRuntimeStatus,
  MetricRecord,
  ProviderMetrics,
  QualityEvaluation,
  ReplaySnapshot,
  SessionRecord,
  StudioState,
  Workflow,
  WorkflowNode,
  WorkflowRunRecord,
  WorkflowRunResult
} from "./types";
import {
  collectCompressionPackets,
  compactDigest,
  formatMetric,
  maybeCompression,
  metricText,
  onEnterOrSpace,
  qualityLabel,
  tryReadNumber,
  type CompressionSelection,
  type DrawerTab,
  type Mode
} from "./uiUtils";

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
  const [qualityRecords, setQualityRecords] = useState<Array<{ id: string; target_type: string; target_id: string; evaluation: QualityEvaluation }>>([]);
  const [localRuntime, setLocalRuntime] = useState<LocalRuntimeStatus | null>(null);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [connectors, setConnectors] = useState<ConnectorRecord[]>([]);
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  const [replaySnapshots, setReplaySnapshots] = useState<ReplaySnapshot[]>([]);
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRunRecord[]>([]);
  const [benchmarkProfiles, setBenchmarkProfiles] = useState<BenchmarkProfile[]>([]);
  const [benchmarkRuns, setBenchmarkRuns] = useState<BenchmarkRun[]>([]);
  const [directAdapters, setDirectAdapters] = useState<DirectRuntimeAdapterInfo[]>([]);
  const [benchmarkResult, setBenchmarkResult] = useState<BenchmarkRun | null>(null);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [workflow, setWorkflow] = useState<Workflow>(defaultWorkflow);
  const [runResult, setRunResult] = useState<WorkflowRunResult | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState("n4");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [historyQuery, setHistoryQuery] = useState("");
  const [provenance, setProvenance] = useState<Record<string, unknown> | null>(null);
  const [compressionPreviewResult, setCompressionPreviewResult] = useState<CompressionPreview | null>(null);
  const [compressionSelection, setCompressionSelection] = useState<CompressionSelection | null>(null);
  const [compressionCompare, setCompressionCompare] = useState<CompressionSelection | null>(null);
  const importRef = useRef<HTMLInputElement | null>(null);

  const latestMessage = chat[chat.length - 1];
  const latestMetric = metrics[metrics.length - 1]?.metric;
  const latestQuality = (latestMetric?.quality_eval as QualityEvaluation | undefined) ?? qualityRecords[qualityRecords.length - 1]?.evaluation;
  const latestProviderMetrics = latestMetric?.provider_metrics as ProviderMetrics | undefined;
  const branches = state?.branches?.length ? state.branches : ["corelm"];

  const refresh = useCallback(async () => {
    try {
      const health = await api.health();
      const [
        nextChat,
        nextLedger,
        nextMetrics,
        nextQuality,
        nextRuntime,
        nextWorkflows,
        nextConnectors,
        nextSettings,
        nextReplaySnapshots,
        nextWorkflowRuns,
        nextBenchmarkProfiles,
        nextBenchmarkRuns,
        nextDirectAdapters,
        nextState,
        nextSessions
      ] = await Promise.all([
        api.chat(sessionId),
        api.ledger(sessionId),
        api.metrics(sessionId),
        api.quality(sessionId),
        api.localRuntime("ollama"),
        api.workflows(),
        api.connectors(),
        api.settings(),
        api.replaySnapshots(sessionId),
        api.workflowRuns(sessionId),
        api.benchmarkProfiles(),
        api.benchmarkRuns(sessionId),
        api.directRuntimeAdapters(),
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
      apply(
        nextQuality as
          | { status: "fulfilled"; value: Array<{ id: string; target_type: string; target_id: string; evaluation: QualityEvaluation }> }
          | { status: "rejected" },
        setQualityRecords
      );
      apply(nextRuntime as { status: "fulfilled"; value: LocalRuntimeStatus } | { status: "rejected" }, setLocalRuntime);
      apply(nextConnectors as { status: "fulfilled"; value: ConnectorRecord[] } | { status: "rejected" }, setConnectors);
      apply(nextSettings as { status: "fulfilled"; value: Record<string, unknown> } | { status: "rejected" }, setSettings);
      apply(nextReplaySnapshots as { status: "fulfilled"; value: ReplaySnapshot[] } | { status: "rejected" }, setReplaySnapshots);
      apply(nextWorkflowRuns as { status: "fulfilled"; value: WorkflowRunRecord[] } | { status: "rejected" }, setWorkflowRuns);
      apply(nextBenchmarkProfiles as { status: "fulfilled"; value: BenchmarkProfile[] } | { status: "rejected" }, setBenchmarkProfiles);
      apply(nextBenchmarkRuns as { status: "fulfilled"; value: BenchmarkRun[] } | { status: "rejected" }, setBenchmarkRuns);
      apply(nextDirectAdapters as { status: "fulfilled"; value: DirectRuntimeAdapterInfo[] } | { status: "rejected" }, setDirectAdapters);
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
    setBenchmarkResult(null);
  }, [sessionId]);

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
    setStatus("busy");
    setReadout("building compression preview...");
    try {
      const result = await api.compressionPreview({
        text: inputText,
        branch,
        compression: {
          steps: ["sanitize", "clean", "dedupe", "canonicalize", "schema_extract", "hash_compress", "contradiction_tag"],
          allow_raw_commit: true
        }
      });
      setCompressionPreviewResult(result);
      setDrawerOpen(true);
      setDrawerTab("compression");
      setReadout(`compression ${result.compression_ratio.toFixed(3)} | ${compactDigest(result.digest)}`);
      setStatus("online");
    } catch (error) {
      setReadout(error instanceof Error ? error.message : "compression preview failed");
      setStatus("online");
    }
  }

  function openCompression(packet: CompressionPreview | null, label: string, compare = false) {
    const selection = { label, packet };
    if (compare) {
      setCompressionCompare(selection);
    } else {
      setCompressionSelection(selection);
    }
    setMode("console");
    setDrawerOpen(true);
    setDrawerTab("compression");
    setReadout(packet ? `compression ${label} | ${compactDigest(packet.digest)}` : "no compression metadata available");
  }

  async function inspectCompressionTarget(targetType: string, targetId: string, label: string, compare = false) {
    try {
      const result = await api.compressionLookup(sessionId, targetType, targetId);
      const first = result.packets[0];
      openCompression(first?.packet ?? null, first?.label ?? label, compare);
    } catch {
      openCompression(null, label, compare);
    }
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
    setBenchmarkResult(null);
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

  async function ensureLocalRuntime(config: Record<string, unknown>) {
    setStatus("busy");
    try {
      const status = await api.ensureLocalRuntime("ollama", config);
      setLocalRuntime(status);
      setReadout(status.healthy ? "ollama runtime ready" : `ollama runtime unavailable: ${status.last_error ?? "not healthy"}`);
      setStatus("online");
    } catch (error) {
      setReadout(error instanceof Error ? error.message : "runtime start failed");
      setStatus("online");
    }
  }

  async function runBenchmarkProfile(profileId: string) {
    setStatus("busy");
    setReadout(`running benchmark ${profileId}...`);
    try {
      const result = await api.runBenchmark({ profile_id: profileId, session_id: sessionId, branch });
      setBenchmarkResult(result);
      const passed = Boolean((result.summary?.verdict as Record<string, unknown> | undefined)?.passed);
      setReadout(`benchmark ${result.run_id ?? result.id ?? profileId} ${passed ? "passed" : String(result.summary?.status ?? "complete")}`);
      await refresh();
    } catch (error) {
      setReadout(error instanceof Error ? error.message : "benchmark run failed");
      setStatus("online");
    }
  }

  async function saveBenchmarkProfile(profile: BenchmarkProfile) {
    await api.saveBenchmarkProfile(profile);
    setReadout(`saved benchmark profile ${profile.name}`);
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
          <button className={mode === "console" ? "active" : ""} aria-pressed={mode === "console"} onClick={() => setMode("console")}>
            <Terminal size={18} /> Console
          </button>
          <button className={mode === "flow" ? "active" : ""} aria-pressed={mode === "flow"} onClick={() => setMode("flow")}>
            <Network size={18} /> Flow Studio
          </button>
          <button className={mode === "benchmark" ? "active" : ""} aria-pressed={mode === "benchmark"} onClick={() => setMode("benchmark")}>
            <Activity size={18} /> Benchmark Studio
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
            <select
              value={sessionId}
              onChange={(event) => {
                setBenchmarkResult(null);
                setSessionId(event.target.value);
              }}
            >
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
        <div className="palette" role="dialog" aria-modal="true" aria-label="Command palette">
          <div className="palette-inner">
            <button onClick={() => setPaletteOpen(false)}>
              <Archive size={17} /> Close
            </button>
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

            <MetricsStrip metric={latestMetric} quality={latestQuality} providerMetrics={latestProviderMetrics} />

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
                <button className={drawerTab === "history" ? "active" : ""} aria-pressed={drawerTab === "history"} onClick={() => setDrawerTab("history")}>
                  <History size={16} /> History
                </button>
                <button className={drawerTab === "compression" ? "active" : ""} aria-pressed={drawerTab === "compression"} onClick={() => setDrawerTab("compression")}>
                  <Braces size={16} /> Compression
                </button>
                <button className={drawerTab === "connectors" ? "active" : ""} aria-pressed={drawerTab === "connectors"} onClick={() => setDrawerTab("connectors")}>
                  <Route size={16} /> Connectors
                </button>
                <button className={drawerTab === "settings" ? "active" : ""} aria-pressed={drawerTab === "settings"} onClick={() => setDrawerTab("settings")}>
                  <Settings size={16} /> Settings
                </button>
              </div>
              {drawerTab === "history" && (
                <HistoryPanel
                  query={historyQuery}
                  setQuery={setHistoryQuery}
                  chat={filteredChat}
                  ledger={ledger}
                  metrics={metrics}
                  qualityRecords={qualityRecords}
                  provenance={provenance}
                  replaySnapshots={replaySnapshots}
                  workflowRuns={workflowRuns}
                  onRoute={routeLatest}
                  onPromote={promoteLatest}
                  onInspectCompression={openCompression}
                  onLookupCompression={inspectCompressionTarget}
                />
              )}
              {drawerTab === "compression" && (
                <CompressionPanel
                  preview={compressionPreviewResult}
                  selection={compressionSelection}
                  compare={compressionCompare}
                  inputText={inputText}
                  onPreview={previewCompression}
                  onClearCompare={() => setCompressionCompare(null)}
                />
              )}
              {drawerTab === "connectors" && (
                <ConnectorPanel
                  connectors={connectors}
                  branch={branch}
                  runtime={localRuntime}
                  onRun={runConnectorIntoCore}
                  onSave={saveConnector}
                  onDelete={deleteConnector}
                  onEnsureRuntime={ensureLocalRuntime}
                />
              )}
              {drawerTab === "settings" && <SettingsPanel state={state} settings={settings} onUpdate={updateStudioSettings} />}
            </aside>
          )}
        </section>
      ) : mode === "flow" ? (
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
          onInspectCompression={openCompression}
        />
      ) : (
        <BenchmarkStudio
          profiles={benchmarkProfiles}
          runs={benchmarkRuns}
          adapters={directAdapters}
          latestRun={benchmarkResult}
          state={state}
          latestMetric={latestMetric}
          sessionId={sessionId}
          branch={branch}
          onRun={runBenchmarkProfile}
          onSave={saveBenchmarkProfile}
          onInspectCompression={openCompression}
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

function MetricsStrip({
  metric,
  quality,
  providerMetrics
}: {
  metric: Record<string, unknown> | undefined;
  quality?: QualityEvaluation | null;
  providerMetrics?: ProviderMetrics;
}) {
  const available = providerMetrics?.provider_metrics_available ?? Boolean(metric?.provider_metrics_available);
  const cards = [
    ["provider", available ? "available" : "unavailable"],
    ["latency", metricText(metric, "provider_total_latency_ms", " ms", 1)],
    ["load", metricText(metric, "provider_load_latency_ms", " ms", 1)],
    ["prompt", metricText(metric, "prompt_tokens", "", 0)],
    ["completion", metricText(metric, "completion_tokens", "", 0)],
    ["total", metricText(metric, "total_tokens", "", 0)],
    ["gen t/s", metricText(metric, "generation_tokens_per_second", "", 1)],
    ["prompt t/s", metricText(metric, "prompt_tokens_per_second", "", 1)],
    ["e2e t/s", metricText(metric, "end_to_end_tokens_per_second", "", 1)],
    ["compression", metricText(metric, "compression_ratio_proxy", "", 3)],
    ["quality", qualityLabel(quality)]
  ];
  return (
    <div className="metrics-strip" role="status" aria-live="polite" aria-label="Run metrics">
      {cards.map(([label, value]) => (
        <span key={label} className={label === "provider" && !available ? "muted" : ""}>
          <strong>{label}</strong>
          {value}
        </span>
      ))}
    </div>
  );
}

function HistoryPanel({
  query,
  setQuery,
  chat,
  ledger,
  metrics,
  qualityRecords,
  provenance,
  replaySnapshots,
  workflowRuns,
  onRoute,
  onPromote,
  onInspectCompression,
  onLookupCompression
}: {
  query: string;
  setQuery: (value: string) => void;
  chat: ChatMessage[];
  ledger: LedgerMirror[];
  metrics: MetricRecord[];
  qualityRecords: Array<{ id: string; target_type: string; target_id: string; evaluation: QualityEvaluation }>;
  provenance: Record<string, unknown> | null;
  replaySnapshots: ReplaySnapshot[];
  workflowRuns: WorkflowRunRecord[];
  onRoute: () => Promise<void>;
  onPromote: () => Promise<void>;
  onInspectCompression: (packet: CompressionPreview | null, label: string, compare?: boolean) => void;
  onLookupCompression: (targetType: string, targetId: string, label: string, compare?: boolean) => Promise<void>;
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
        {chat.map((message) => {
          const packet = maybeCompression(message.metadata?.compression);
          return (
            <article
              key={message.id}
              className={`chat-item ${packet ? "inspectable" : ""}`}
              role={packet ? "button" : undefined}
              tabIndex={packet ? 0 : undefined}
              onKeyDown={packet ? onEnterOrSpace(() => onInspectCompression(packet, `chat:${message.id}`)) : undefined}
              onClick={() => {
                if (packet) {
                  onInspectCompression(packet, `chat:${message.id}`);
                }
              }}
            >
              <div>
                <span>{message.origin}</span>
                <span>{message.branch}</span>
                <span>{message.format}</span>
                {packet && <span>compression</span>}
              </div>
              <p>{message.content}</p>
              {packet && (
                <div className="item-actions">
                  <button
                    onClick={(event) => {
                      event.stopPropagation();
                      onInspectCompression(packet, `chat:${message.id}`);
                    }}
                  >
                    Inspect
                  </button>
                  <button
                    onClick={(event) => {
                      event.stopPropagation();
                      onInspectCompression(packet, `chat:${message.id}`, true);
                    }}
                  >
                    Compare
                  </button>
                </div>
              )}
            </article>
          );
        })}
      </div>
      <h2>Ledger</h2>
      <div className="ledger-list">
        {ledger.slice(-6).map((entry) => {
          const packet = maybeCompression(entry.metadata?.compression);
          return (
          <article
            key={`${entry.session_id}-${entry.entry_id}`}
            className={`ledger-item ${packet ? "inspectable" : ""}`}
            role="button"
            tabIndex={0}
            onKeyDown={onEnterOrSpace(() => void onLookupCompression("ledger_entry", entry.entry_id, `ledger:${entry.entry_id}`))}
            onClick={() => void onLookupCompression("ledger_entry", entry.entry_id, `ledger:${entry.entry_id}`)}
          >
            <strong>{entry.entry_id}</strong>
            <span>{entry.branch}</span>
            <p>{entry.raw_text}</p>
            <div className="item-actions">
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  void onLookupCompression("ledger_entry", entry.entry_id, `ledger:${entry.entry_id}`);
                }}
              >
                Inspect
              </button>
              {packet && (
                <button
                  onClick={(event) => {
                    event.stopPropagation();
                    onInspectCompression(packet, `ledger:${entry.entry_id}`, true);
                  }}
                >
                  Compare
                </button>
              )}
            </div>
          </article>
          );
        })}
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
        {workflowRuns.slice(-4).map((run) => {
          const packets = collectCompressionPackets(run, `workflow:${run.id}`);
          return (
            <article
              key={run.id}
              className={`trace-item ${run.status} ${packets.length ? "inspectable" : ""}`}
              role="button"
              tabIndex={0}
              onKeyDown={onEnterOrSpace(() => void onLookupCompression("workflow_run", run.id, `workflow:${run.id}`))}
              onClick={() => void onLookupCompression("workflow_run", run.id, `workflow:${run.id}`)}
            >
              <strong>{run.workflow_id}</strong>
              <span>{run.created_at}</span>
              <code>{run.status}</code>
              {packets.length > 0 && (
                <div className="item-actions trace-actions">
                  <button
                    onClick={(event) => {
                      event.stopPropagation();
                      onInspectCompression(packets[0].packet, packets[0].label);
                    }}
                  >
                    Inspect
                  </button>
                  {packets[1] && (
                    <button
                      onClick={(event) => {
                        event.stopPropagation();
                        onInspectCompression(packets[1].packet, packets[1].label, true);
                      }}
                    >
                      Compare
                    </button>
                  )}
                </div>
              )}
            </article>
          );
        })}
      </div>
      <h2>Provider Metrics</h2>
      <div className="ledger-list">
        {metrics.slice(-4).map((item) => (
          <article key={item.id} className="ledger-item">
            <strong>{String(item.metric.provider_model ?? item.event_id ?? item.id)}</strong>
            <span>{item.metric.provider_metrics_available ? "provider metrics available" : "provider metrics unavailable"}</span>
            <p>
              latency {metricText(item.metric, "provider_total_latency_ms", " ms", 1)} | generation {metricText(item.metric, "generation_tokens_per_second", "", 1)} t/s
            </p>
          </article>
        ))}
      </div>
      <h2>Quality Eval</h2>
      <div className="ledger-list">
        {qualityRecords.slice(-4).map((item) => (
          <article key={item.id} className="ledger-item">
            <strong>{item.target_type}</strong>
            <span>{item.target_id}</span>
            <p>
              score {qualityLabel(item.evaluation)} | {item.evaluation.modes.join(", ")}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}

function ConnectorPanel({
  connectors,
  branch,
  runtime,
  onRun,
  onSave,
  onDelete,
  onEnsureRuntime
}: {
  connectors: ConnectorRecord[];
  branch: string;
  runtime: LocalRuntimeStatus | null;
  onRun: (connectorType: string, config: Record<string, unknown>) => Promise<void>;
  onSave: (connector: ConnectorRecord) => Promise<void>;
  onDelete: (connectorId: string) => Promise<void>;
  onEnsureRuntime: (config: Record<string, unknown>) => Promise<void>;
}) {
  const inbound = [
    { type: "manual_text", label: "Manual text" },
    { type: "openai_compatible_llm", label: "OpenAI-compatible" },
    { type: "lm_studio", label: "LM Studio gemma-4" },
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
  const [ollamaConfig, setOllamaConfig] = useState<Record<string, unknown>>(defaultOllamaConfig);

  function setOllamaField(key: string, value: unknown) {
    setOllamaConfig((current) => ({ ...current, [key]: value }));
  }

  function applyDeterministicPreset() {
    setOllamaConfig((current) => ({
      ...current,
      mock: false,
      stream: false,
      deterministic_benchmark: true,
      seed: current.seed === "" ? 0 : current.seed,
      temperature: 0,
      top_p: 1,
      top_k: 40,
      num_predict: 128
    }));
  }

  const nonDefaultSampling = ["seed", "temperature", "top_p", "top_k", "min_p", "repeat_penalty", "repeat_last_n", "num_ctx", "num_predict", "stop"].some(
    (key) => String(ollamaConfig[key] ?? "") !== String(defaultOllamaConfig[key] ?? "")
  );
  const numberConstraints: Record<string, { min?: number; max?: number; step?: number }> = {
    seed: { step: 1 },
    temperature: { min: 0, step: 0.05 },
    top_p: { min: 0, max: 1, step: 0.01 },
    top_k: { min: 0, step: 1 },
    min_p: { min: 0, max: 1, step: 0.01 },
    repeat_penalty: { min: 0, step: 0.05 },
    repeat_last_n: { min: -1, step: 1 },
    num_ctx: { min: 1, step: 1 },
    num_predict: { min: -2, step: 1 }
  };

  function runConfigFor(type: string): Record<string, unknown> {
    if (type === "lm_studio") {
      return {
        base_url: "http://127.0.0.1:1234/v1",
        model: "gemma-4-e4b-uncensored-hauhaucs-aggressive",
        prompt,
        text: prompt,
        mock: false,
        temperature: 0,
        branch
      };
    }
    if (type === "ollama_local_model") {
      const stop = String(ollamaConfig.stop ?? "")
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean);
      return {
        ...ollamaConfig,
        prompt,
        text: prompt,
        ...(stop.length > 0 ? { stop } : {}),
        auto_start: true,
        branch
      };
    }
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

  function selectConnectorType(type: string) {
    setConnectorType(type);
    if (type === "lm_studio" && connectorName === "Mock ingress") {
      setConnectorName("LM Studio gemma-4");
    }
    if (type === "ollama_local_model" && connectorName === "Mock ingress") {
      setConnectorName("Ollama benchmark");
    }
  }

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
          <select value={connectorType} onChange={(event) => selectConnectorType(event.target.value)}>
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
        {connectorType === "ollama_local_model" && (
          <div className="sampling-controls">
            <div className="sampling-header">
              <h2>Ollama Settings</h2>
              {nonDefaultSampling && <span className="connector-pill">non-default sampling</span>}
            </div>
            <div className="runtime-status">
              <strong>{runtime?.healthy ? "Ollama ready" : "Ollama not running"}</strong>
              <span>{runtime?.base_url ?? String(ollamaConfig.base_url ?? "http://127.0.0.1:11434")}</span>
              {runtime?.last_error && <span>{runtime.last_error}</span>}
              <button onClick={() => void onEnsureRuntime(runConfigFor("ollama_local_model"))}>
                <Play size={16} /> Start Local Server
              </button>
            </div>
            <label className="stacked-field">
              Base URL
              <input value={String(ollamaConfig.base_url ?? "")} onChange={(event) => setOllamaField("base_url", event.target.value)} />
            </label>
            <label className="stacked-field">
              Model
              <input value={String(ollamaConfig.model ?? "")} onChange={(event) => setOllamaField("model", event.target.value)} />
            </label>
            <label className="stacked-field">
              System
              <textarea value={String(ollamaConfig.system ?? "")} onChange={(event) => setOllamaField("system", event.target.value)} />
            </label>
            <div className="toggle-row">
              <label>
                <input type="checkbox" checked={Boolean(ollamaConfig.mock)} onChange={(event) => setOllamaField("mock", event.target.checked)} />
                Mock
              </label>
              <label>
                <input type="checkbox" checked={Boolean(ollamaConfig.raw)} onChange={(event) => setOllamaField("raw", event.target.checked)} />
                Raw
              </label>
              <label>
                <input type="checkbox" checked={Boolean(ollamaConfig.stream)} onChange={(event) => setOllamaField("stream", event.target.checked)} />
                Stream
              </label>
            </div>
            <label className="stacked-field">
              Format
              <select value={String(ollamaConfig.format ?? "plain")} onChange={(event) => setOllamaField("format", event.target.value)}>
                <option value="plain">plain</option>
                <option value="json">json</option>
                <option value="schema">schema</option>
              </select>
            </label>
            <details className="advanced-panel" open>
              <summary>Advanced sampling</summary>
              <div className="sampling-grid">
                {[
                  ["seed", "Seed"],
                  ["temperature", "Temperature"],
                  ["top_p", "Top P"],
                  ["top_k", "Top K"],
                  ["min_p", "Min P"],
                  ["repeat_penalty", "Repeat Penalty"],
                  ["repeat_last_n", "Repeat Last N"],
                  ["num_ctx", "Context"],
                  ["num_predict", "Predict"]
                ].map(([key, label]) => (
                  <label key={key} className="stacked-field">
                    {label}
                    <input
                      type="number"
                      min={numberConstraints[key]?.min}
                      max={numberConstraints[key]?.max}
                      step={numberConstraints[key]?.step}
                      value={String(ollamaConfig[key] ?? "")}
                      onChange={(event) => {
                        if (event.target.value === "") {
                          setOllamaField(key, "");
                          return;
                        }
                        const next = Number(event.target.value);
                        if (Number.isFinite(next)) {
                          setOllamaField(key, next);
                        }
                      }}
                    />
                  </label>
                ))}
              </div>
              <label className="stacked-field">
                Stop
                <textarea value={String(ollamaConfig.stop ?? "")} onChange={(event) => setOllamaField("stop", event.target.value)} />
              </label>
              <label className="stacked-field">
                Keep alive
                <input value={String(ollamaConfig.keep_alive ?? "")} onChange={(event) => setOllamaField("keep_alive", event.target.value)} />
              </label>
            </details>
            <div className="inline-actions">
              <button onClick={applyDeterministicPreset}>
                <Settings size={16} /> Benchmark Preset
              </button>
              <button onClick={() => setOllamaConfig(defaultOllamaConfig)}>
                <RefreshCw size={16} /> Reset
              </button>
            </div>
          </div>
        )}
        <div className="inline-actions">
          <button onClick={() => void onRun(connectorType, runConfig)}>
            <Play size={16} /> Run through Core
          </button>
          <button onClick={() => void onSave(connectorDraft())}>
            <Save size={16} /> Save Profile
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

function BenchmarkStudio({
  profiles,
  runs,
  adapters,
  latestRun,
  state,
  latestMetric,
  sessionId,
  branch,
  onRun,
  onSave,
  onInspectCompression
}: {
  profiles: BenchmarkProfile[];
  runs: BenchmarkRun[];
  adapters: DirectRuntimeAdapterInfo[];
  latestRun: BenchmarkRun | null;
  state: StudioState | null;
  latestMetric: Record<string, unknown> | undefined;
  sessionId: string;
  branch: string;
  onRun: (profileId: string) => Promise<void>;
  onSave: (profile: BenchmarkProfile) => Promise<void>;
  onInspectCompression: (packet: CompressionPreview | null, label: string, compare?: boolean) => void;
}) {
  const [selectedProfileId, setSelectedProfileId] = useState(profiles[0]?.id ?? "builtin-runtime-conformance");
  const selectedProfile = profiles.find((profile) => profile.id === selectedProfileId) ?? profiles[0];
  const activeRun = latestRun ?? runs[runs.length - 1] ?? null;
  const activeSummary = activeRun?.summary ?? {};
  const selectedStrict = Boolean(selectedProfile?.strict || selectedProfile?.mode === "strict_direct");
  const activeStrict = Boolean(activeRun?.strict || activeRun?.profile?.strict || activeSummary.mode === "strict_direct");
  const verdict = activeSummary.verdict as Record<string, unknown> | undefined;
  const verdictPassed = Boolean(verdict?.passed);
  const firstTrial = activeRun?.trials?.[0];
  const compressionPacket = maybeCompression(firstTrial?.ingest?.compression);

  function duplicateProfile() {
    if (!selectedProfile) {
      return;
    }
    const cloned: BenchmarkProfile = {
      ...selectedProfile,
      id: `${selectedProfile.id}-copy-${Date.now().toString(36)}`,
      name: `${selectedProfile.name} Copy`,
      strict: false,
      mode: selectedProfile.mode === "strict_direct" ? "seeded_stochastic" : selectedProfile.mode
    };
    void onSave(cloned);
  }

  return (
    <section className="benchmark-layout" data-testid="benchmark-mode">
      <section className="benchmark-rail">
        <div className="benchmark-header">
          <div>
            <span className="readout-kicker">benchmark studio</span>
            <h2>Direct Runtime Profiles</h2>
          </div>
          <span className={`strict-label ${selectedStrict ? "strict" : "bridge"}`}>{selectedStrict ? "STRICT PROFILE" : "NON-STRICT"}</span>
        </div>
        <label className="stacked-field">
          Profile
          <select value={selectedProfile?.id ?? ""} onChange={(event) => setSelectedProfileId(event.target.value)}>
            {profiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.name}
              </option>
            ))}
          </select>
        </label>
        {selectedProfile && (
          <article className="benchmark-profile-card">
            <div>
              <strong>{selectedProfile.name}</strong>
              <span>{selectedProfile.mode}</span>
              <span>{selectedProfile.adapter_id}</span>
            </div>
            <p>{selectedProfile.description}</p>
            <div className="inline-actions">
              <button onClick={() => void onRun(selectedProfile.id)}>
                <Play size={16} /> Run Profile
              </button>
              <button onClick={duplicateProfile}>
                <Save size={16} /> Clone
              </button>
            </div>
          </article>
        )}
        <h2>Adapters</h2>
        <div className="adapter-list">
          {adapters.map((adapter) => (
            <article key={adapter.adapter_id} className="adapter-card">
              <div>
                <strong>{adapter.adapter_id}</strong>
                <span>{adapter.runtime_family}</span>
              </div>
              <span className={`strict-label ${adapter.strict_eligible && adapter.availability === "available" ? "strict" : "bridge"}`}>
                {adapter.support_classification ?? (adapter.strict_eligible ? "DIRECT" : "NON-STRICT")}
              </span>
              <p>{adapter.availability}{adapter.last_error ? `: ${adapter.last_error}` : ""}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="benchmark-main">
        <div className="benchmark-header">
          <div>
            <span className="readout-kicker">run result</span>
            <h2>{String(activeRun?.run_id ?? activeRun?.id ?? "No benchmark run")}</h2>
          </div>
          <span className={`strict-label ${verdictPassed ? "strict" : "bridge"}`}>{runVerdictLabel(activeStrict, verdictPassed, activeSummary.status)}</span>
        </div>

        <div className="benchmark-grid">
          <MetricPanel
            title="Determinism Inspector"
            rows={[
              ["output repeat", summaryMetric(activeSummary, "exact_output_repeat_rate")],
              ["token repeat", summaryMetric(activeSummary, "exact_token_sequence_repeat_rate")],
              ["trace hash", summaryMetric(activeSummary, "token_trace_hash_repeat_rate")],
              ["replay", summaryMetric(activeSummary, "replay_consistency_score")]
            ]}
          />
          <MetricPanel
            title="Runtime Telemetry"
            rows={[
              ["total", summaryMetric(activeSummary, "total_ms", " ms", 1)],
              ["ttft", summaryMetric(activeSummary, "ttft_ms", " ms", 1)],
              ["decode t/s", summaryMetric(activeSummary, "decode_tps", "", 1)],
              ["peak ram", summaryMetric(activeSummary, "peak_ram_mb", " MB", 1)]
            ]}
          />
          <MetricPanel
            title="Core LM State"
            rows={[
              ["session", sessionId],
              ["branch", branch],
              ["ledger", String(state?.stats?.ledger_entries ?? 0)],
              ["state norm", tryReadNumber(latestMetric?.state_norm)],
              ["invariants", String(state?.stats?.invariant_violations ?? 0)],
              ["digest", compactDigest(state?.digest)]
            ]}
          />
          <MetricPanel
            title="Compression"
            rows={[
              ["ratio", summaryMetric(activeSummary, "overall_compression_ratio")],
              ["duplicates", summaryMetric(activeSummary, "duplicate_items_removed", "", 0)],
              ["schema fields", summaryMetric(activeSummary, "schema_fields_extracted", "", 0)],
              ["void tokens", summaryMetric(activeSummary, "void_token_count", "", 0)]
            ]}
          />
        </div>

        <div className="inline-actions">
          <button onClick={() => onInspectCompression(compressionPacket, `benchmark:${activeRun?.run_id ?? activeRun?.id ?? "latest"}`)}>
            <Braces size={16} /> Inspect Compression
          </button>
          <button onClick={() => onInspectCompression(compressionPacket, `benchmark:${activeRun?.run_id ?? activeRun?.id ?? "latest"}`, true)}>
            <Layers size={16} /> Compare
          </button>
        </div>

        <h2>Recent Runs</h2>
        <div className="trace-list">
          {runs.slice(-6).map((run) => {
            const summary = run.summary ?? {};
            const passed = Boolean((summary.verdict as Record<string, unknown> | undefined)?.passed);
            return (
              <article key={String(run.id ?? run.run_id)} className={`trace-item ${passed ? "ok" : "warning"}`}>
                <strong>{String(run.run_id ?? run.id)}</strong>
                <span>{String(summary.profile_name ?? run.profile_id ?? "profile")}</span>
                <code>{String(summary.status ?? run.status ?? "unknown")}</code>
                <span>{summaryMetric(summary, "exact_output_repeat_rate")}</span>
              </article>
            );
          })}
        </div>
      </section>
    </section>
  );
}

function MetricPanel({ title, rows }: { title: string; rows: Array<[string, string]> }) {
  return (
    <section className="metric-panel">
      <h2>{title}</h2>
      {rows.map(([label, value]) => (
        <span key={label}>
          <strong>{label}</strong>
          {value}
        </span>
      ))}
    </section>
  );
}

function summaryMetric(summary: Record<string, unknown>, key: string, suffix = "", digits = 3): string {
  const value = summary[key];
  return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(digits)}${suffix}` : "n/a";
}

function runVerdictLabel(strict: boolean, passed: boolean, status: unknown): string {
  if (strict && passed) {
    return "STRICT PASS";
  }
  if (strict) {
    const normalized = String(status ?? "pending").toUpperCase();
    return normalized === "BLOCKED" ? "STRICT BLOCKED" : `STRICT ${normalized}`;
  }
  return passed ? "PASS" : String(status ?? "PENDING");
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
  onImport,
  onInspectCompression
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
  onInspectCompression: (packet: CompressionPreview | null, label: string, compare?: boolean) => void;
}) {
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const [dragging, setDragging] = useState<{ id: string; offsetX: number; offsetY: number } | null>(null);
  const [edgeSource, setEdgeSource] = useState(selectedNode.id);
  const [edgeTarget, setEdgeTarget] = useState(selectedNode.id);

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

  function addEdge() {
    if (!edgeSource || !edgeTarget || edgeSource === edgeTarget) {
      return;
    }
    const id = `e-${edgeSource}-${edgeTarget}`;
    if (workflow.edges.some((edge) => edge.source === edgeSource && edge.target === edgeTarget)) {
      return;
    }
    setWorkflow({ ...workflow, edges: [...workflow.edges, { id, source: edgeSource, target: edgeTarget }] });
  }

  function deleteEdge(edgeId: string) {
    setWorkflow({ ...workflow, edges: workflow.edges.filter((edge) => edge.id !== edgeId) });
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
          <h2>Edges</h2>
          <div className="edge-editor">
            <select value={edgeSource} onChange={(event) => setEdgeSource(event.target.value)}>
              {workflow.nodes.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.id}
                </option>
              ))}
            </select>
            <select value={edgeTarget} onChange={(event) => setEdgeTarget(event.target.value)}>
              {workflow.nodes.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.id}
                </option>
              ))}
            </select>
            <button onClick={addEdge}>Add Edge</button>
          </div>
          <div className="edge-list">
            {workflow.edges.map((edge) => (
              <article key={edge.id}>
                <span>
                  {edge.source} -&gt; {edge.target}
                </span>
                <button onClick={() => deleteEdge(edge.id)}>Delete</button>
              </article>
            ))}
          </div>
          <h2>Trace</h2>
          {runResult?.quality_eval && (
            <div className="quality-box">
              <strong>Quality {qualityLabel(runResult.quality_eval)}</strong>
              <span>{runResult.quality_eval.modes.join(", ")}</span>
            </div>
          )}
          <div className="trace-list">
            {(runResult?.trace ?? []).map((item) => {
              const packet = maybeCompression(item.compression);
              const provider = item.provider_metrics as ProviderMetrics | undefined;
              return (
                <article key={String(item.node_id)} className={`trace-item ${String(item.status)}`}>
                  <strong>{String(item.node_id)}</strong>
                  <span>{String(item.type)}</span>
                  <code>{String(item.status)}</code>
                  {(packet || provider) && (
                    <div className="trace-detail">
                      {provider && <span>latency {formatMetric(provider.derived.provider_total_latency_ms, " ms", 1)}</span>}
                      {provider && <span>gen {formatMetric(provider.derived.generation_tokens_per_second, "", 1)} t/s</span>}
                      {packet && (
                        <button onClick={() => onInspectCompression(packet, `workflow:${runResult?.run_id ?? "current"}.${String(item.node_id)}`)}>
                          Inspect compression
                        </button>
                      )}
                    </div>
                  )}
                </article>
              );
            })}
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
