import { Panel } from "../common/Panel";
import { formatDuration } from "../../utils/files";

export function TimelinePanel({ timeline }) {
  return (
    <Panel title="Agent Timeline">
      <div className="timeline-list">
        {timeline.length ? (
          timeline.map((entry, index) => (
            <article key={`${entry.agent}-${entry.timestamp}-${index}`} className="timeline-item">
              <strong>{entry.agent}</strong>
              <span>{entry.status || "-"}</span>
              <span>{formatDuration(entry.duration_ms)}</span>
              <small>{(entry.tool_calls || []).map((toolCall) => toolCall.tool).join(", ") || "No tools"}</small>
            </article>
          ))
        ) : (
          <p className="muted-text">Timeline will appear after a run.</p>
        )}
      </div>
    </Panel>
  );
}
