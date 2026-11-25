<div align="center">

# 🎴 VCardForge

**Zero-dependency · Offline-first vCard (.vcf) contacts toolkit**

*Full vCard parsing & generation implemented from scratch on the Python standard library — library + CLI in one*

[简体中文](README.md) | [繁體中文](README.zh-TW.md) | [English](README.en.md)

`Python 3.8+` · `0 dependencies` · `0 network calls` · `MIT`

</div>

---

## 🎉 Introduction

**VCardForge** turns the `.vcf` address books scattered across phones, messaging apps, and Outlook exports into programmable, cleanable, auditable data. It implements full vCard 2.1 / 3.0 / 4.0 parsing and generation from scratch — using only the Python standard library — and is built for the "data never leaves this machine" scenario.

What sets it apart:

- ✅ **Zero third-party dependencies** — stdlib only, installs in seconds, or just copy the source
- ✅ **Fully offline** — normalization, deduplication, and validation all run locally; contact data never leaves the device
- ✅ **Tolerates dirty data** — vCard 2.1 QUOTED-PRINTABLE, Outlook `item1.` group prefixes, iOS multi-TYPE params, line folding… all handled
- ✅ **Lossless round-trip** — parsing → output preserves every original property; no fields silently dropped

## ✨ Features

| Module | Capability |
|--------|-----------|
| 🔍 **Parsing** | vCard 2.1 / 3.0 / 4.0; line unfolding; QUOTED-PRINTABLE / BASE64 decoding; `item1.` prefix stripping; graceful per-property error recovery |
| ☎️ **Phone normalization** | E.164-style output; Chinese mobile / landline detection; full-width digit correction; cross-format unification (`+86 138...` vs `138-0013-8000`) |
| 🧬 **Smart dedup** | Weighted scoring: phone 0.60 + email 0.30 + name 0.10; union-find transitive merging; keeps the most complete record per group |
| 📦 **Multi-file merge** | Merge & dedup any number of .vcf files in one pass; output vCard 3.0 / 4.0 |
| 📊 **Export** | JSON (with normalized numbers) / CSV (UTF-8 BOM so Excel opens it cleanly) |
| 🛡️ **Validation** | 10 rules (R01–R10): missing FN/N, invalid VERSION, unparseable dates, duplicate numbers, malformed emails… CI-gate ready (exit code 2 on errors) |
| 🎂 **Birthday reminders** | Birthdays within the next N days; Feb 29 gracefully falls back to Feb 28 in non-leap years |
| 🔄 **Version conversion** | 2.1 / 3.0 → 3.0 / 4.0, auto-filling UID / FN / N |

## 🚀 Quick Start

**Option 1: pip**

```bash
pip install .
```

**Option 2: single-file, no install**

```bash
# Grab vcardforge-*.pyz from the Releases page, then:
python3 vcardforge-1.0.0.pyz --help
```

**Option 3: as a library**

```python
from vcardforge import parse_file, dedup_contacts, write_file

contacts = parse_file("contacts.vcf")
clean, report = dedup_contacts(contacts)
print(f"{len(contacts)} in -> {len(clean)} after dedup")
write_file(clean, "clean.vcf", version="4.0")
```

## 📖 Usage Guide

### The six CLI subcommands

```bash
vcardforge info      contacts.vcf              # 📊 overview: counts / version mix / field stats
vcardforge validate  contacts.vcf --detail     # 🛡️ 10-rule validation, exit code 2 on errors
vcardforge merge a.vcf b.vcf -o merged.vcf -v # 🧬 merge + smart dedup
vcardforge export    contacts.vcf -o out.csv   # 📦 export CSV / JSON
vcardforge birthdays contacts.vcf --days 30    # 🎂 birthdays in the next 30 days
vcardforge convert   old.vcf -o new.vcf --version 4.0  # 🔄 version conversion
```

### Typical workflow: export → clean → re-import

```bash
vcardforge validate all-contacts.vcf --detail
vcardforge merge app1.vcf phone.vcf backup.vcf -o clean.vcf -v
vcardforge export clean.vcf -o contacts.csv
vcardforge convert clean.vcf -o clean4.vcf --version 4.0
```

### Python API cheat sheet

```python
from vcardforge import (
    parse_text, parse_file,      # parsing
    write_text, write_file,      # generation (3.0 / 4.0)
    normalize_phone,             # E.164-style normalization
    dedup_contacts, merge_contacts,  # dedup / multi-source merge
    to_json, to_csv,             # export
    validate_contacts,           # validation report
)

c = parse_file("x.vcf")[0]
c.display_name                      # best display name (FN > N > nickname > ORG)
normalize_phone("13800138000")      # -> '+8613800138000'
```

### Validation rules at a glance

| Rule | Meaning | Severity |
|------|---------|----------|
| R01/R02 | Missing FN / missing N | warning |
| R03 | Both FN and N missing (imports get rejected) | **error** |
| R04/R05 | Missing VERSION / invalid value | warning / error |
| R06 | Unparseable birthday | warning |
| R07 | Phone has no digits at all | **error** |
| R08/R09 | Duplicate phone within / across contacts | warning |
| R10 | EMAIL missing @ | warning |

## 💡 Design & Iteration

- **v1.0.0**: parsing (2.1/3.0/4.0) · phone normalization · weighted dedup · JSON/CSV export · 10-rule validation · birthday reminders · version conversion · zipapp single-file packaging
- **Roadmap**: fine-grained ADR modeling · lunar-calendar birthdays · PHOTO size statistics · pinyin fuzzy name matching

## 📦 Packaging & Deployment

```bash
# One-click build: single-file CLI (.pyz) + source zip + SHA256 checksums
python3 scripts/build.py
```

Run the test suite:

```bash
python3 -m unittest discover -s tests -v
```

## 🤝 Contributing

Issues and PRs are welcome! Please follow Angular commit conventions (`feat` / `fix` / `docs` / `refactor` / `test` / `chore`) — see [CONTRIBUTING.md](CONTRIBUTING.md).

Two hard rules: **stdlib only**, **never phone home**.

## 📄 License

[MIT](LICENSE) © VCardForge Contributors
