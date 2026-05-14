import type { KeyboardEvent } from "react";
import type { CompressionPreview, QualityEvaluation } from "./types";

export type Mode = "console" | "flow" | "benchmark";
export type DrawerTab = "history" | "compression" | "connectors" | "settings";
export type CompressionSelection = { label: string; packet: CompressionPreview | null };

export function compactDigest(value?: string): string {
  if (!value) {
    return "pending";
  }
  return `${value.slice(0, 10)}...${value.slice(-6)}`;
}

export function tryReadNumber(value: unknown): string {
  return typeof value === "number" ? value.toFixed(3) : "0.000";
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function formatMetric(value: unknown, suffix = "", digits = 1): string {
  const number = asNumber(value);
  if (number === null) {
    return "n/a";
  }
  return `${number.toFixed(digits)}${suffix}`;
}

export function metricText(metric: Record<string, unknown> | undefined, key: string, suffix = "", digits = 1): string {
  return formatMetric(metric?.[key], suffix, digits);
}

export function qualityLabel(evaluation?: QualityEvaluation | null): string {
  if (!evaluation || evaluation.summary_score === null) {
    return "n/a";
  }
  return `${Math.round(evaluation.summary_score * 100)}%`;
}

export function limitText(value: string | null | undefined, expanded: boolean, limit = 2800): string {
  const text = value ?? "";
  return expanded || text.length <= limit ? text : `${text.slice(0, limit)}\n... truncated ...`;
}

export function onEnterOrSpace(action: () => void) {
  return (event: KeyboardEvent) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      action();
    }
  };
}

export function maybeCompression(value: unknown): CompressionPreview | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const packet = value as Partial<CompressionPreview>;
  return typeof packet.canonical_text === "string" && typeof packet.digest === "string" ? (packet as CompressionPreview) : null;
}

export function collectCompressionPackets(value: unknown, label: string, packets: CompressionSelection[] = []): CompressionSelection[] {
  const packet = maybeCompression(value);
  if (packet) {
    packets.push({ label, packet });
    return packets;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => collectCompressionPackets(item, `${label}[${index}]`, packets));
  } else if (value && typeof value === "object") {
    Object.entries(value as Record<string, unknown>).forEach(([key, item]) => collectCompressionPackets(item, `${label}.${key}`, packets));
  }
  return packets;
}
