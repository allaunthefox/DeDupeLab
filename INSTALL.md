# 🧩 Installing Dedupelab

Dedupelab is a self-contained Python tool for cataloging and deduplicating
archives using contextual SHA-256 hashing. It requires **Python 3.9 or newer**.

---

## ⚙️ Quick Setup

### 1. Extract the package
Unzip the release archive anywhere on your system.

```bash
unzip dedupelab_v6_3_contextual_hashing_apache2.zip
cd dedupelab_repo
```

### 2. Run the first scan
Point Dedupelab at any directory you want indexed:

```bash
python3 -m dedupelab.cli scan --root /path/to/data
```

This creates validated `meta.json` files in every subdirectory, describing each
folder’s contents.

---

## 🧪 Optional Acceleration

If you have **pandas** or **cuDF** installed, Dedupelab will automatically
use them to accelerate grouping and deduplication.
No configuration needed — detection is silent.

---

## 🔍 Validation and Integrity

To verify metadata integrity, run:

```bash
python3 -m dedupelab.cli validate --root /path/to/data
```

This ensures every `meta.json` conforms to the internal
`dedupelab_meta_v4.schema.json`.

---

## 📄 License

This project is licensed under the **Apache License 2.0**, included in
`LICENSE` at the repository root.
All code files include SPDX license headers for clarity.

---

## 🧭 Support Philosophy

Dedupelab is designed to be **completely offline and self-describing**.
All schema references are local (`file://./`) so it will always validate and
run, even decades from now, on any compatible Python interpreter.
