# Dedupelab

Important! Dedupelab was written by a combination of LLMs and should not be used on production unless 
you accept what that implies. It works for me, might not work for you. Might delete everything.


Dedupelab is a self-contained system for cataloging and deduplicating files.

It generates self-describing `meta.json` manifests for every folder so that
archives remain readable and verifiable even without the original software.

All operations rely only on local computation and standard data formats.
Dedupelab requires no network access, no external dependencies, and no
assumptions about operating systems, file systems, or environments.

---

## Overview

Dedupelab performs recursive directory scans, identifies unique files using
contextual SHA-256 hashing, and produces metadata that describes each folder’s
structure, file types, and inferred categories.

Every directory receives a `meta.json` manifest that follows the
`dedupelab_meta_v4` schema. These manifests are meant to remain valid and
machine-readable indefinitely.

---

## Features

**Contextual hashing**

Dedupelab uses SHA-256 as its single hashing algorithm.  
Each file also carries a `context_tag` field that distinguishes archived from
unarchived copies.  
This prevents extracted files from being merged with their compressed forms.

**Automatic metadata generation**

Each folder gains a validated `meta.json` listing all files.  
The manifest summarizes totals, categories, and topics in a compact structure.

**Self-validation**

All metadata is validated against an internal JSON Schema before being written.
If validation fails, the manifest is saved as `meta.invalid.json` for review.

**Acceleration when available**

If libraries such as cuDF or pandas are available, Dedupelab will use them for
faster processing.  
If not, it runs entirely in pure Python with the same output.

**Offline operation**

All schema references are local (`file://./`).  
No external services or online validation are ever required.

---

## Installation

Extract the release archive into any directory.

Example layout:

```
dedupelab/
 ├── accelerator.py
 ├── cli.py
 ├── db.py
 ├── scanner.py
 ├── meta_exporter.py
 ├── validator.py
 ├── schemas/
 │    └── dedupelab_meta_v4.schema.json
 ├── MANUAL.md
 ├── LICENSE
 └── README.md
```

Dedupelab runs directly from its folder using the system’s Python interpreter.
No installation or package manager is required.

Example:

```
python3 -m dedupelab.cli scan --root /path/to/data
```

---

## Usage

### Scanning

The `scan` command walks through the specified directory, computes SHA-256
hashes, and generates validated metadata.

#### Android (Termux)
```
python dedupelab/cli.py scan --root /storage/emulated/0/Documents
```

#### Windows (PowerShell)
```
python dedupelab\cli.py scan --root "C:\Users\<name>\Documents"
```

#### Linux (Bash)
```
python3 -m dedupelab.cli scan --root /home/<name>/Documents
```

#### macOS (zsh)
```
python3 -m dedupelab.cli scan --root ~/Documents
```

---

### Validation

To check all generated metadata:

#### Android (Termux)
```
python dedupelab/cli.py validate --root /storage/emulated/0/Documents
```

#### Windows (PowerShell)
```
python dedupelab\cli.py validate --root "C:\Users\<name>\Documents"
```

#### Linux (Bash)
```
python3 -m dedupelab.cli validate --root /home/<name>/Documents
```

#### macOS (zsh)
```
python3 -m dedupelab.cli validate --root ~/Documents
```

Each `meta.json` file is tested against the internal schema, and any
inconsistencies are reported during the run.

---

## Metadata and Output

Every directory receives a `meta.json` file describing its contents.

Example entry:

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
```

Each manifest also includes a summary block that records totals, categories,
and keyword data for quick reference.

---

## Validation and Integrity

The internal schema file `dedupelab_meta_v4.schema.json` defines every field
and constraint.

All references are local, so validation works entirely offline.

The schema follows JSON Schema Draft 2020-12 and the JSON syntax defined in
RFC 8259.

---

## License

Dedupelab is distributed under the Apache License 2.0.

All Python modules include SPDX headers for attribution and license clarity.

```
SPDX-License-Identifier: Apache-2.0
Copyright (c) 2025 Allaun
```

See the `LICENSE` file at the repository root for full terms.

---

## Documentation

Additional reference material, including configuration defaults and schema
definitions, is available in `MANUAL.md` and `INSTALL.md`.

Both documents are included in the distribution archive and require no
external access.
