import { Panel } from "../common/Panel";
import { CodeBlock } from "../common/CodeBlock";

export function RawResultPanel({ result }) {
  return (
    <Panel title="Raw JSON Result">
      <CodeBlock value={result ? JSON.stringify(result, null, 2) : ""} />
    </Panel>
  );
}
