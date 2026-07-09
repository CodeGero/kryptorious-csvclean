# csvclean

> Find and fix CSV file problems — encoding, delimiters, headers, duplicates, types.

[![PyPI](https://img.shields.io/pypi/v/kryptorious-csvclean)](https://pypi.org/project/kryptorious-csvclean/) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Part of the [Kryptorious developer toolkit](https://kryptorious.gumroad.com/l/jbvet) — 31 open-source tools, one $9 lifetime license.

## Install

```bash
pip install kryptorious-csvclean
```

## Quickstart

```bash
printf 'name;age\nAlice;30\n;;\nAlice;30\n' > messy.csv
csvclean clean messy.csv clean.csv --normalize
# -> removes empty row, dedupes, writes comma-delimited clean.csv
```

## Commands

| Command | Description |
|---------|-------------|
| `csvclean check messy.csv` | Analyze a CSV and report all issues (encoding, delimiter, duplicates, type mismatches). |
| `csvclean clean messy.csv clean.csv --normalize` | Write a fixed copy: normalizes delimiter to comma, drops empty/duplicate rows. |
| `csvclean dedupe data.csv deduped.csv` | Remove duplicate data rows. |
| `csvclean stats data.csv` | Show per-column statistics. |



## License

MIT — free for personal and commercial use. The $9 lifetime license adds DevFlow Premium (multi-environment CI/CD, approval gates, infrastructure-as-code). Get it at [kryptorious.gumroad.com/l/jbvet](https://kryptorious.gumroad.com/l/jbvet).
