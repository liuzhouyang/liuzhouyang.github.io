#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "_data" / "publications_config.json"
PUBLICATIONS_PATH = ROOT / "_data" / "publications.yml"


def normalize_title(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def parse_bibtex(text: str) -> tuple[str, str, dict[str, str]]:
    header = re.search(r"@([A-Za-z]+)\s*\{\s*([^,\s]+)\s*,", text)
    if not header:
        raise ValueError("invalid BibTeX header")
    entry_type = header.group(1).lower()
    key = header.group(2)
    fields: dict[str, str] = {}
    for match in re.finditer(r"(?m)^\s*([A-Za-z]+)\s*=\s*\{([^}]*)\}\s*,?\s*$", text):
        fields[match.group(1).lower()] = match.group(2).strip()
    return entry_type, key, fields


def validate(title: str, bibtex: str, expected: dict) -> tuple[str, str, dict[str, str]]:
    if "–" in bibtex or "—" in bibtex:
        raise ValueError(f"{title}: Unicode dash found; use BibTeX-safe '--' for page ranges")
    if re.search(r"(?mi)^\s*month\s*=", bibtex):
        raise ValueError(f"{title}: month field is intentionally disallowed to avoid macro-format errors")

    entry_type, key, fields = parse_bibtex(bibtex)
    if entry_type != expected["type"].lower():
        raise ValueError(f"{title}: type {entry_type!r} != {expected['type']!r}")
    if key != expected["key"]:
        raise ValueError(f"{title}: key {key!r} != {expected['key']!r}")

    for field, wanted in expected.items():
        if field in {"type", "key"}:
            continue
        actual = fields.get(field.lower())
        if actual is None:
            raise ValueError(f"{title}: missing field {field}")
        if field == "title":
            ok = normalize_title(actual) == normalize_title(str(wanted))
        elif field == "doi":
            ok = actual.lower() == str(wanted).lower()
        else:
            ok = " ".join(actual.split()) == " ".join(str(wanted).split())
        if not ok:
            raise ValueError(f"{title}: {field}={actual!r} != {wanted!r}")

    return entry_type, key, fields


def main() -> None:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    pubs = yaml.safe_load(PUBLICATIONS_PATH.read_text(encoding="utf-8")) or []
    by_title = {normalize_title(p.get("title", "")): p for p in pubs}

    keys: set[str] = set()
    validated = 0

    for title in cfg.get("pinned_titles", []):
        override = cfg.get("overrides", {}).get(title, {})
        bibtex = str(override.get("copy_bibtex", "")).strip()
        expected = override.get("citation_expect")
        if not bibtex or not expected:
            raise RuntimeError(f"{title}: missing vetted copy_bibtex/citation_expect")

        _, key, _ = validate(title, bibtex, expected)
        if key in keys:
            raise RuntimeError(f"duplicate BibTeX key: {key}")
        keys.add(key)

        pub = by_title.get(normalize_title(title))
        if not pub:
            raise RuntimeError(f"{title}: selected publication missing from publications.yml")
        pub["copy_bibtex"] = bibtex
        validated += 1
        print(f"[citation] VERIFIED {key}: {title}")

    if validated != len(cfg.get("pinned_titles", [])):
        raise RuntimeError("not all pinned citations were validated")

    PUBLICATIONS_PATH.write_text(
        yaml.safe_dump(pubs, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )
    print(f"Validated and registered {validated} canonical BibTeX entries.")


if __name__ == "__main__":
    main()
