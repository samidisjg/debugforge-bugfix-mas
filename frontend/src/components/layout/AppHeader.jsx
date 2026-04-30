export function AppHeader({ onClearData }) {
  return (
    <header className="hero">
      <div className="hero-layout">
        <div className="hero-copy-block">
          <div className="hero-topbar">
            <div className="mode-pill" aria-hidden="true">
              <span className="mode-dot" />
              <span>Agent Mode: Live Workflow</span>
            </div>
            <button type="button" className="secondary-button hero-clear-button" onClick={onClearData}>
              Clear Data
            </button>
          </div>
          <h1>Bug Fixing MAS Console</h1>
          <p className="hero-copy">
            Visual command center for the locally hosted multi-agent bug fixing backend. Configure runs, monitor the
            workflow, inspect all 4 agents separately, and download generated report and patch artifacts.
          </p>
        </div>

        <div className="agent-3d" aria-hidden="true">
          <div className="robot-agent-3d">
            <div className="robot-antenna" />
            <div className="robot-head">
              <span className="robot-eye" />
              <span className="robot-eye" />
            </div>
            <div className="robot-body">
              <span className="robot-core" />
            </div>
            <div className="robot-arm left" />
            <div className="robot-arm right" />
          </div>
        </div>
      </div>
    </header>
  );
}
