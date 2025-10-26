Dedupelab
Dedupelab is a self-contained system for cataloging and deduplicating files. It generates self-describing meta.json manifests for every folder, allowing archives to remain readable and verifiable even without the original software.
All operations rely only on local computation and standard data formats. Dedupelab requires no network access, no external dependencies, and no assumptions about operating systems, file systems, or environments.

Overview
Dedupelab performs recursive directory scans, identifies unique files using contextual SHA-256 hashing, and produces compact metadata describing the structure, file types, and inferred categories of each folder.
Each directory receives a meta.json manifest conforming to the dedupelab_meta_v4 schema. These manifests are designed to remain valid and machine-readable indefinitely.

Features
Contextual hashing Uses SHA-256 as the sole hashing algorithm and assigns each file a context_tag field to differentiate between archived and unarchived instances. This prevents accidental merging of extracted and containerized duplicates.
Automatic metadata generation Each folder receives a validated meta.json manifest that lists all files and summarizes totals, categories, and topics.
Self-validation Dedupelab validates every manifest against its internal JSON Schema before writing it. Invalid manifests are quarantined as meta.invalid.json.
Acceleration when available If the environment provides data processing libraries such as cuDF or pandas, Dedupelab will use them automatically. Otherwise, it falls back to pure Python execution without functional difference.
Offline operation All schema references are local (file://./) and every component runs without network access.

Installation
Extract the release archive into any directory. The structure will appear as follows:
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
Dedupelab runs directly from its folder using the system’s Python interpreter.
Example:
python3 -m dedupelab.cli scan --root /path/to/data
No installation or package manager is required.

Usage
Scanning
The scan command walks through the specified directory, computes SHA-256 hashes, and generates validated metadata.
dedupelab scan --root /path/to/data
Validation
To verify all generated metadata:
dedupelab validate --root /path/to/data
This checks every meta.json file against the local schema and reports any structural inconsistencies.
Rebuilding
To rebuild a database from existing manifests:
dedupelab rebuild --root /path/to/data

Metadata and Output
Each directory receives a file named meta.json containing descriptive and structural information.
Example entry:
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
Each manifest also includes a summary block describing totals, categories, and keywords.

Validation and Integrity
The internal schema file dedupelab_meta_v4.schema.json defines all structural and field constraints. Schema references are self-contained, allowing Dedupelab to validate data without external resources.
The schema adheres to JSON Schema Draft 2020-12 and the JSON syntax defined in RFC 8259.

License
Dedupelab is distributed under the Apache License 2.0. All Python modules include SPDX headers for attribution and license clarity.
SPDX-License-Identifier: Apache-2.0
Copyright (c) 2025 Allaun
See the LICENSE file at the repository root for full terms.

Documentation
Further reference material, including configuration defaults and schema definitions, can be found in MANUAL.md and INSTALL.md. These documents are included within the distribution archive and contain no external references.
