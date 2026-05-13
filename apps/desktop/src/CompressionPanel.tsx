import { Boxes, Braces, Clipboard, RefreshCw } from "lucide-react";
import { useState } from "react";
import type { CompressionPreview } from "./types";
import { compactDigest, limitText, type CompressionSelection } from "./uiUtils";

type CompressionPanelProps = {
  preview: CompressionPreview | null;
  selection: CompressionSelection | null;
  compare: CompressionSelection | null;
  inputText: string;
  onPreview: () => Promise<void>;
  onClearCompare: () => void;
};

export function CompressionPanel({ preview, selection, compare, inputText, onPreview, onClearCompare }: CompressionPanelProps) {
  const active = selection ? selection.packet : preview;
  const label = selection?.label ?? (preview ? "preview" : "current input");
  const rawText = active?.raw_text ?? inputText;
  const compressedText = active?.canonical_text ?? "";
  const rawBytes = active?.raw_length ?? rawText.length;
  const compressedBytes = active?.canonical_length ?? compressedText.length;
  const [expanded, setExpanded] = useState(false);
  const displayRaw = limitText(rawText, expanded);
  const displayCanonical = limitText(compressedText, expanded);
  const rows = buildLineDiff(displayRaw, displayCanonical);

  return (
    <div className="drawer-body compression-inspector">
      <div className="inline-actions">
        <button onClick={() => void onPreview()}>
          <Boxes size={16} /> Run Preview
        </button>
        <button onClick={() => setExpanded((value) => !value)}>
          <Braces size={16} /> {expanded ? "Collapse" : "Expand"}
        </button>
      </div>
      <h2>{label}</h2>
      {!active && <span className="empty-state">No compression metadata available</span>}
      {active && (
        <>
          <section className="compression-metrics">
            <span>ratio {active.compression_ratio.toFixed(3)}</span>
            <span>raw {rawBytes} bytes</span>
            <span>compressed {compressedBytes} bytes</span>
            <span>
              tokens {active.token_proxy_before ?? "n/a"} -&gt; {active.token_proxy_after ?? "n/a"}
            </span>
            <span>digest {compactDigest(active.digest)}</span>
            <span>canonical {active.canonical_length ?? compressedText.length} chars</span>
          </section>
          <h2>Steps</h2>
          <div className="step-list">
            {active.steps.map((step) => (
              <span key={step}>{step}</span>
            ))}
          </div>
          <div className="copy-row">
            <button onClick={() => void navigator.clipboard?.writeText(rawText)}>
              <Clipboard size={15} /> Raw
            </button>
            <button onClick={() => void navigator.clipboard?.writeText(compressedText)}>
              <Clipboard size={15} /> Canonical
            </button>
          </div>
          <h2>Pipeline</h2>
          <div className="pipeline-panel">
            <Stage label="Raw input" value={displayRaw} />
            <Stage label="Sanitized" value={limitText(active.sanitized_text, expanded)} />
            <Stage label="Cleaned" value={limitText(active.cleaned_text, expanded)} />
            <Stage label="Deduped" value={limitText(active.deduped_text, expanded)} />
            <Stage label="Canonical" value={limitText(active.canonicalized_text ?? compressedText, expanded)} />
          </div>
          <h2>Raw -&gt; Canonical</h2>
          <div className="compression-diff">
            <strong>Raw</strong>
            <strong>Canonical</strong>
            {rows.map((row, index) => (
              <div key={`${row.kind}-${index}`} className={`diff-row ${row.kind}`}>
                <pre>{row.raw || " "}</pre>
                <pre>{row.compressed || " "}</pre>
              </div>
            ))}
          </div>
          <h2>Annotations</h2>
          <pre className="json-preview">{JSON.stringify(active.structured_extraction ?? active.annotations, null, 2)}</pre>
          {active.contradiction_candidates.length > 0 && (
            <>
              <h2>Contradiction Markers</h2>
              <div className="step-list">
                {active.contradiction_candidates.map((candidate) => (
                  <span key={candidate}>{candidate}</span>
                ))}
              </div>
            </>
          )}
          {compare?.packet && (
            <>
              <h2>Compare: {compare.label}</h2>
              <section className="compression-metrics">
                <span>ratio {compare.packet.compression_ratio.toFixed(3)}</span>
                <span>digest {compactDigest(compare.packet.digest)}</span>
                <span>raw {compare.packet.raw_length ?? compare.packet.raw_text.length} chars</span>
                <span>canonical {compare.packet.canonical_length ?? compare.packet.canonical_text.length} chars</span>
              </section>
              <div className="inline-actions">
                <button onClick={onClearCompare}>
                  <RefreshCw size={16} /> Clear Compare
                </button>
              </div>
              <div className="compression-diff">
                <strong>Active canonical</strong>
                <strong>Compare canonical</strong>
                {buildLineDiff(limitText(active.canonical_text, expanded), limitText(compare.packet.canonical_text, expanded)).map((row, index) => (
                  <div key={`compare-${row.kind}-${index}`} className={`diff-row ${row.kind}`}>
                    <pre>{row.raw || " "}</pre>
                    <pre>{row.compressed || " "}</pre>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

function Stage({ label, value }: { label: string; value?: string | null }) {
  return (
    <article>
      <strong>{label}</strong>
      <pre>{value || "not captured for this packet"}</pre>
    </article>
  );
}

function buildLineDiff(rawText: string, compressedText: string) {
  const rawLines = rawText.split("\n");
  const compressedLines = compressedText.split("\n");
  const count = Math.max(rawLines.length, compressedLines.length, 1);
  return Array.from({ length: count }, (_, index) => {
    const raw = rawLines[index] ?? "";
    const compressed = compressedLines[index] ?? "";
    const kind = raw === compressed ? "same" : raw && compressed ? "changed" : raw ? "removed" : "added";
    return { raw, compressed, kind };
  });
}
