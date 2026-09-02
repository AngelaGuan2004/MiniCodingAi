import { useEffect, useMemo, useState } from "react";
import {
  Bot,
  Check,
  ChevronDown,
  ChevronRight,
  Circle,
  Code2,
  File,
  Folder,
  FolderOpen,
  GitCompare,
  LoaderCircle,
  Play,
  RefreshCw,
  Sparkles,
  SquareTerminal,
  Wrench,
  X,
} from "lucide-react";

function buildTree(files) {
  const root = {};

  for (const path of files) {
    let current = root;
    const parts = path.split("/");

    parts.forEach((part, index) => {
      if (!current[part]) {
        current[part] = {
          __file: index === parts.length - 1,
          __children: {},
        };
      }
      current = current[part].__children;
    });
  }

  return root;
}

function FileTreeNode({ name, node, depth = 0 }) {
  const [open, setOpen] = useState(true);
  const children = Object.entries(node.__children);
  const isFile = node.__file;

  if (isFile) {
    return (
      <div className="tree-row" style={{ paddingLeft: 14 + depth * 15 }}>
        <File size={14} />
        <span>{name}</span>
      </div>
    );
  }

  return (
    <>
      <button
        className="tree-row tree-folder"
        style={{ paddingLeft: 10 + depth * 15 }}
        onClick={() => setOpen(!open)}
      >
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        {open ? <FolderOpen size={14} /> : <Folder size={14} />}
        <span>{name}</span>
      </button>

      {open &&
        children.map(([childName, child]) => (
          <FileTreeNode
            key={childName}
            name={childName}
            node={child}
            depth={depth + 1}
          />
        ))}
    </>
  );
}

function WorkspaceTree({ files }) {
  const tree = useMemo(() => buildTree(files), [files]);

  if (!files.length) {
    return <div className="muted-block">No files found</div>;
  }

  return Object.entries(tree).map(([name, node]) => (
    <FileTreeNode key={name} name={name} node={node} />
  ));
}

function StatusPill({ running, error, hasResult }) {
  if (running) {
    return (
      <div className="status-pill running">
        <LoaderCircle size={12} className="spin" />
        Running
      </div>
    );
  }

  if (error) {
    return (
      <div className="status-pill failed">
        <X size={12} />
        Failed
      </div>
    );
  }

  if (hasResult) {
    return (
      <div className="status-pill success">
        <Check size={12} />
        Complete
      </div>
    );
  }

  return (
    <div className="status-pill ready">
      <Circle size={8} fill="currentColor" />
      Ready
    </div>
  );
}

function EventIcon({ event }) {
  if (event.type === "step") return <Sparkles size={15} />;
  if (event.type === "tool_start") {
    if (event.tool === "run_command") return <SquareTerminal size={15} />;
    if (event.tool === "write_file") return <Code2 size={15} />;
    return <Wrench size={15} />;
  }
  if (event.type === "file_changed") return <GitCompare size={15} />;
  if (event.type === "command_result") {
    return event.returncode === 0 ? (
      <Check size={15} />
    ) : (
      <X size={15} />
    );
  }
  if (event.type === "agent_done") return <Check size={15} />;

  return <Bot size={15} />;
}

function eventTitle(event) {
  switch (event.type) {
    case "agent_start":
      return "Agent started";
    case "step":
      return `Step ${event.step}`;
    case "tool_start":
      return event.tool;
    case "file_changed":
      return `Modified ${event.path}`;
    case "command_result":
      return event.returncode === 0
        ? "Command succeeded"
        : "Command failed";
    case "agent_done":
      return "Task completed";
    default:
      return event.type;
  }
}

function eventDetail(event) {
  if (event.type === "tool_start") return event.detail;
  if (event.type === "command_result") return event.command;
  if (event.type === "file_changed") return event.path;
  return "";
}

function Timeline({ events, running }) {
  const visible = events.filter((event) => event.type !== "agent_start");

  if (!visible.length) {
    return (
      <div className="empty-state">
        <div className="empty-icon">
          {running ? (
            <LoaderCircle size={22} className="spin" />
          ) : (
            <Sparkles size={22} />
          )}
        </div>
        <strong>{running ? "Starting agent…" : "Ready for a task"}</strong>
        <span>
          Agent actions, file changes and command execution will appear here.
        </span>
      </div>
    );
  }

  return (
    <div className="timeline">
      {visible.map((event, index) => (
        <div
          className={`timeline-item event-${event.type}`}
          key={`${event.type}-${index}`}
        >
          <div className="timeline-rail">
            <div className="timeline-icon">
              <EventIcon event={event} />
            </div>
            {index < visible.length - 1 && <div className="timeline-line" />}
          </div>

          <div className="timeline-content">
            <div className="timeline-title">
              <span>{eventTitle(event)}</span>

              {event.type === "command_result" && (
                <span
                  className={
                    event.returncode === 0
                      ? "mini-badge success"
                      : "mini-badge failed"
                  }
                >
                  exit {event.returncode}
                </span>
              )}
            </div>

            {eventDetail(event) && (
              <code className="timeline-detail">{eventDetail(event)}</code>
            )}
          </div>
        </div>
      ))}

      {running && (
        <div className="timeline-working">
          <LoaderCircle size={14} className="spin" />
          Agent is thinking
        </div>
      )}
    </div>
  );
}

function DiffViewer({ events }) {
  const changes = events.filter((event) => event.type === "file_changed");

  if (!changes.length) {
    return (
      <div className="panel-empty">
        <GitCompare size={28} />
        <strong>No changes yet</strong>
        <span>Modified files and unified diffs will appear here.</span>
      </div>
    );
  }

  return (
    <div className="diff-list">
      {changes.map((change, index) => (
        <div className="diff-card" key={`${change.path}-${index}`}>
          <div className="diff-header">
            <File size={14} />
            {change.path}
          </div>

          <div className="diff-code">
            {(change.diff || "No textual difference")
              .split("\n")
              .map((line, lineIndex) => {
                let className = "diff-line";

                if (line.startsWith("+++") || line.startsWith("---")) {
                  className += " diff-meta";
                } else if (line.startsWith("+")) {
                  className += " diff-add";
                } else if (line.startsWith("-")) {
                  className += " diff-remove";
                } else if (line.startsWith("@@")) {
                  className += " diff-range";
                }

                return (
                  <div className={className} key={lineIndex}>
                    {line || " "}
                  </div>
                );
              })}
          </div>
        </div>
      ))}
    </div>
  );
}

function Terminal({ events }) {
  const commands = events.filter(
    (event) => event.type === "command_result"
  );

  if (!commands.length) {
    return (
      <div className="panel-empty">
        <SquareTerminal size={28} />
        <strong>No command output</strong>
        <span>Test and shell results will appear here.</span>
      </div>
    );
  }

  return (
    <div className="terminal">
      {commands.map((event, index) => (
        <div className="terminal-entry" key={index}>
          <div className="terminal-command">
            <span className="prompt">$</span>
            {event.command}
          </div>

          {event.stdout && (
            <pre className="terminal-output">{event.stdout}</pre>
          )}

          {event.stderr && (
            <pre className="terminal-output terminal-error">
              {event.stderr}
            </pre>
          )}

          <div
            className={
              event.returncode === 0
                ? "terminal-exit success-text"
                : "terminal-exit failed-text"
            }
          >
            process exited with code {event.returncode}
          </div>
        </div>
      ))}
    </div>
  );
}

function ResultPanel({ result }) {
  if (!result) {
    return (
      <div className="panel-empty">
        <Bot size={28} />
        <strong>No result yet</strong>
        <span>The agent's final response will appear here.</span>
      </div>
    );
  }

  return <div className="result-content">{result}</div>;
}

export default function App() {
  const [files, setFiles] = useState([]);
  const [task, setTask] = useState(
    "项目中存在一个与除法功能相关的 bug。请自行探索代码，定位并修复问题。不要修改测试来规避问题。修复后运行相关测试，测试通过后结束。"
  );
  const [events, setEvents] = useState([]);
  const [result, setResult] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("changes");

  async function loadFiles() {
    try {
      const response = await fetch("/api/files");
      if (!response.ok) throw new Error("Failed to load workspace");
      setFiles(await response.json());
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadFiles();
  }, []);

  async function runAgent() {
    if (!task.trim() || running) return;

    setRunning(true);
    setEvents([]);
    setResult("");
    setError("");

    try {
      const response = await fetch("/api/run", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ task }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Agent execution failed");
      }

      setEvents(data.events || []);
      setResult(data.result || "");
      setTab(
        data.events?.some((event) => event.type === "file_changed")
          ? "changes"
          : "result"
      );

      await loadFiles();
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Code2 size={18} />
          </div>
          <div>
            <strong>MiniAgent</strong>
            <span>Coding Runtime</span>
          </div>
        </div>

        <div className="topbar-meta">
          <div className="workspace-chip">
            <Folder size={13} />
            Workspace
          </div>

          <div className="model-chip">
            <Sparkles size={13} />
            GLM
          </div>

          <StatusPill
            running={running}
            error={error}
            hasResult={Boolean(result)}
          />
        </div>
      </header>

      <div className="workspace-layout">
        <aside className="sidebar">
          <div className="sidebar-heading">
            <span>EXPLORER</span>

            <button
              className="icon-button"
              onClick={loadFiles}
              title="Refresh files"
            >
              <RefreshCw size={14} />
            </button>
          </div>

          <div className="workspace-name">
            <ChevronDown size={14} />
            <FolderOpen size={15} />
            <strong>workspace</strong>
          </div>

          <div className="file-tree">
            <WorkspaceTree files={files} />
          </div>

          <div className="sidebar-footer">
            <div className="connection-dot" />
            Local runtime connected
          </div>
        </aside>

        <main className="main-panel">
          <section className="hero">
            <div className="hero-eyebrow">
              <Sparkles size={14} />
              Autonomous coding workspace
            </div>

            <h1>What should MiniAgent build or fix?</h1>

            <p>
              MiniAgent explores your workspace, edits source files and
              validates changes using local tools.
            </p>
          </section>

          <section className="composer">
            <textarea
              value={task}
              onChange={(event) => setTask(event.target.value)}
              placeholder="Describe a bug, feature or coding task…"
              disabled={running}
            />

            <div className="composer-footer">
              <div className="composer-hint">
                <Wrench size={13} />
                Local tools · Workspace isolated
              </div>

              <button
                className="run-button"
                onClick={runAgent}
                disabled={running || !task.trim()}
              >
                {running ? (
                  <>
                    <LoaderCircle size={15} className="spin" />
                    Running
                  </>
                ) : (
                  <>
                    <Play size={15} fill="currentColor" />
                    Run Agent
                  </>
                )}
              </button>
            </div>
          </section>

          {error && (
            <div className="error-banner">
              <X size={15} />
              {error}
            </div>
          )}

          <section className="run-section">
            <div className="section-title">
              <div>
                <span className="section-label">AGENT RUN</span>
                <h2>Execution timeline</h2>
              </div>

              {events.length > 0 && (
                <span className="event-count">
                  {events.length} events
                </span>
              )}
            </div>

            <Timeline events={events} running={running} />
          </section>
        </main>

        <aside className="inspector">
          <div className="inspector-tabs">
            <button
              className={tab === "changes" ? "active" : ""}
              onClick={() => setTab("changes")}
            >
              <GitCompare size={14} />
              Changes
            </button>

            <button
              className={tab === "terminal" ? "active" : ""}
              onClick={() => setTab("terminal")}
            >
              <SquareTerminal size={14} />
              Terminal
            </button>

            <button
              className={tab === "result" ? "active" : ""}
              onClick={() => setTab("result")}
            >
              <Bot size={14} />
              Result
            </button>
          </div>

          <div className="inspector-content">
            {tab === "changes" && <DiffViewer events={events} />}
            {tab === "terminal" && <Terminal events={events} />}
            {tab === "result" && <ResultPanel result={result} />}
          </div>
        </aside>
      </div>
    </div>
  );
}