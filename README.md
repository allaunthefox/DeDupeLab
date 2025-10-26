# 🧩 Dedupelab v6.3 — Contextual Hashing Edition

**Autonomous file cataloging and deduplication for long-term data survival.**
Deduplab scans entire drives or archives, generates self-describing `meta.json`
manifests, and ensures every folder can be understood even if the original
program is lost.

---

## 🌐 Overview

Deduplab builds an **index of meaning** — not just hashes. Each folder receives
a `meta.json` that lists its files, categories, and inferred topics. All
manifests follow strict [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259) JSON
and [JSON Schema Draft 2020-12](https://json-schema.org/) compliance.

If the code disappears, the manifests remain a **map of your data**.

---

## ⚙️ Features

- 🔒 **Context-aware SHA-256 hashing**  
  Distinguishes archived (`.zip`, `.tar`, `.7z`, etc.) from unarchived files via
  `context_tag`.

- 🧠 **Semantic metadata export**  
  Each folder gets a compact `meta.json` describing its contents, file types,
  and topics.

- 🚀 **Hybrid acceleration**  
  Uses [cuDF](https://rapids.ai) (GPU) or [pandas](https://pandas.pydata.org)
  automatically if available; falls back to pure Python otherwise.

- 🧪 **Self-linting and schema-validated**  
  Every run re-lints its source and validates manifests on write.

- 🧰 **Zero-dependency core**  
  Runs even on minimal Python environments. All extras are optional.

---

## 🔒 Hashing & Deduplication

Deduplab uses a single algorithm — **SHA-256** — and tags each file with its
storage context.

| Example | sha256 | context_tag | Result |
|----------|---------|-------------|---------|
| Same file on disk | `abc123...` | `unarchived` | Duplicate |
| Same file inside ZIP | `abc123...` | `archived` | Separate entity |

This prevents cross-context collisions while keeping identical files grouped
correctly.

---

## 🧾 Manifest Schema (`meta_v4`)

Example entry inside a folder’s `meta.json`:

```json
{
  "name": "IMG_1204.JPG",
  "size": 2837423,
  "mtime": 1730090400,
  "sha256": "1f3cbe02b1a5a73d9b8b8a2c248a693a2c6bbf2aeb8ecbb92b09db4a6c420e19",
  "mime": "image/jpeg",
  "category": "image",
  "subtype": "photo",
  "topic": "beach",
  "context_tag": "unarchived"
}
