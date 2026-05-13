from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from .security import sanitize_obj, sanitize_text


KEY_VALUE_PATTERN = re.compile(r"^\s*([A-Za-z0-9_\- ]+)\.([A-Za-z0-9_\- ]+)\s*[:=]\s*(.+?)\s*$")


@dataclass
class CompressionResult:
    raw_text: str
    canonical_text: str
    steps: list[str] = field(default_factory=list)
    annotations: list[dict[str, Any]] = field(default_factory=list)
    digest: str = ""
    compression_ratio: float = 1.0
    contradiction_candidates: list[str] = field(default_factory=list)
    sanitized_text: str | None = None
    cleaned_text: str | None = None
    deduped_text: str | None = None
    canonicalized_text: str | None = None
    structured_extraction: list[dict[str, Any]] = field(default_factory=list)
    raw_length: int = 0
    canonical_length: int = 0
    token_proxy_before: int = 0
    token_proxy_after: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "sanitized_text": self.sanitized_text,
            "cleaned_text": self.cleaned_text,
            "deduped_text": self.deduped_text,
            "canonicalized_text": self.canonicalized_text,
            "canonical_text": self.canonical_text,
            "steps": list(self.steps),
            "annotations": list(self.annotations),
            "structured_extraction": list(self.structured_extraction),
            "digest": self.digest,
            "compression_ratio": self.compression_ratio,
            "raw_length": self.raw_length,
            "canonical_length": self.canonical_length,
            "token_proxy_before": self.token_proxy_before,
            "token_proxy_after": self.token_proxy_after,
            "contradiction_candidates": list(self.contradiction_candidates),
        }


def stable_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def clean_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.strip() for line in normalized.splitlines())
    return re.sub(r"\n{3,}", "\n\n", normalized).strip()


def dedupe_lines(text: str) -> str:
    seen: set[str] = set()
    output: list[str] = []
    for line in text.splitlines():
        key = line.strip().lower()
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        output.append(line)
    return "\n".join(output).strip()


def summarize_text(text: str, max_words: int = 80) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + " ..."


def canonicalize(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def chunk_text(text: str, max_chars: int = 1200) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    current = ""
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph_parts = [paragraph[index:index + max_chars] for index in range(0, len(paragraph), max_chars)] or [""]
        for part in paragraph_parts:
            if len(current) + len(part) + 2 <= max_chars:
                current = f"{current}\n\n{part}".strip()
                continue
            if current:
                chunks.append(current)
            current = part
    if current:
        chunks.append(current)
    return chunks

def extract_annotations(text: str, branch: str) -> list[dict[str, Any]]:
    annotations: list[dict[str, Any]] = []
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            payload = json.loads(stripped)
            if isinstance(payload, dict):
                subject = str(payload.get("subject") or payload.get("entity") or "json")
                for key, value in payload.items():
                    if key in {"subject", "entity"}:
                        continue
                    if isinstance(value, (str, int, float, bool)):
                        annotations.append(
                            {
                                "branch": branch,
                                "subject": subject,
                                "attribute": str(key),
                                "value": str(value),
                                "claim_type": "fact",
                                "tags": ["schema-extracted"],
                            }
                        )
        except json.JSONDecodeError:
            pass
    for line in text.splitlines():
        match = KEY_VALUE_PATTERN.match(line)
        if not match:
            continue
        subject, attribute, value = match.groups()
        annotations.append(
            {
                "branch": branch,
                "subject": subject.strip(),
                "attribute": attribute.strip(),
                "value": value.strip(),
                "claim_type": "fact",
                "tags": ["key-value-extracted"],
            }
        )
    return annotations


def contradiction_candidates(text: str) -> list[str]:
    markers = ("correction:", "instead of", "supersedes", "not ", "changed to", "replace ")
    lowered = text.lower()
    return [marker.strip() for marker in markers if marker in lowered]


def preprocess_payload(
    raw_text: str,
    branch: str,
    options: dict[str, Any] | None = None,
    annotations: list[dict[str, Any]] | None = None,
) -> CompressionResult:
    options = options or {}
    steps = options.get(
        "steps",
        [
            "sanitize",
            "clean",
            "dedupe",
            "canonicalize",
            "schema_extract",
            "hash_compress",
            "contradiction_tag",
        ],
    )
    raw = sanitize_text(str(raw_text))
    text = raw
    sanitized = text
    cleaned: str | None = None
    deduped: str | None = None
    canonicalized: str | None = None
    applied: list[str] = ["sanitize"]
    if "clean" in steps or "text_cleaning" in steps:
        text = clean_text(text)
        cleaned = text
        applied.append("clean")
    if "dedupe" in steps or "deduplication" in steps:
        text = dedupe_lines(text)
        deduped = text
        applied.append("dedupe")
    if "summarize" in steps or "summarization" in steps:
        text = summarize_text(text, int(options.get("summary_words", 80)))
        applied.append("summarize")
    if "canonicalize" in steps or "canonicalization" in steps:
        text = canonicalize(text)
        canonicalized = text
        applied.append("canonicalize")
    extracted: list[dict[str, Any]] = []
    if "schema_extract" in steps or "key_value_extract" in steps or "schema extraction" in steps:
        extracted = extract_annotations(text, branch)
        applied.append("schema_extract")
    if annotations:
        extracted.extend(sanitize_obj(annotations))
    digest = stable_digest(text)
    if options.get("allow_raw_commit") and not extracted:
        extracted.append(
            {
                "branch": branch,
                "subject": "note",
                "attribute": digest[:12],
                "value": text[:500],
                "claim_type": "note",
                "tags": ["raw-commit-allowed"],
            }
        )
    compressed = text
    if "chunk" in steps or "chunking" in steps:
        chunks = chunk_text(text, int(options.get("max_chars", 1200)))
        compressed = "\n\n".join(f"[chunk:{index + 1}/{len(chunks)}]\n{chunk}" for index, chunk in enumerate(chunks))
        applied.append("chunking")
    if "hash_compress" in steps or "lightweight embedding/hash compression" in steps:
        if options.get("hash_only", True):
            compressed = f"sha256:{digest}\nbytes:{len(text.encode('utf-8'))}\npreview:{text[:240]}"
        applied.append("hash_compress")
    candidates = contradiction_candidates(text) if "contradiction_tag" in steps else []
    if candidates:
        applied.append("contradiction_tag")
    ratio = len(compressed.encode("utf-8")) / max(1, len(raw.encode("utf-8")))
    return CompressionResult(
        raw_text=raw,
        canonical_text=compressed,
        steps=applied,
        annotations=extracted,
        digest=digest,
        compression_ratio=ratio,
        contradiction_candidates=candidates,
        sanitized_text=sanitized,
        cleaned_text=cleaned,
        deduped_text=deduped,
        canonicalized_text=canonicalized or text,
        structured_extraction=extracted,
        raw_length=len(raw),
        canonical_length=len(compressed),
        token_proxy_before=len(raw.split()),
        token_proxy_after=len(compressed.split()),
    )
