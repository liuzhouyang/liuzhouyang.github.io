#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "_data" / "publications_config.json"
PUBLICATIONS_PATH = ROOT / "_data" / "publications.yml"
USER_AGENT = "academic-homepage-citation-sync/1.0 (+https://github.com/liuzhouyang/liuzhouyang.github.io)"


def normalize_title(title: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", title.lower()).split())


def fetch_crossref_bibtex(doi: str) -> str:
    encoded = urllib.parse.quote(doi, safe="")
    url = f"https://api.crossref.org/works/{encoded}/transform/application/x-bibtex"
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/x-bibtex,text/plain;q=0.9,*/*;q=0.1",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                text = resp.read().decode("utf-8").strip()
            if not text.startswith("@") or len(text) < 80:
                raise RuntimeError(f"unexpected BibTeX payload: {text[:120]!r}")
            return text
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"failed to fetch DOI BibTeX for {doi}: {last}")


def main() -> None:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    pubs = yaml.safe_load(PUBLICATIONS_PATH.read_text(encoding="utf-8")) or []
    by_title = {normalize_title(p.get("title", "")): p for p in pubs}

    refreshed = 0
    removed = 0

    for title, override in cfg.get("overrides", {}).items():
        pub = by_title.get(normalize_title(title))
        if not pub:
            continue

        static_bibtex = override.get("copy_bibtex")
        doi = override.get("citation_doi")

        if static_bibtex:
            pub["copy_bibtex"] = str(static_bibtex).strip()
            refreshed += 1
            print(f"[citation] static source: {title}")
            continue

        if doi:
            try:
                pub["copy_bibtex"] = fetch_crossref_bibtex(str(doi))
                refreshed += 1
                print(f"[citation] Crossref publisher metadata: {title} ({doi})")
            except Exception as exc:
                if "copy_bibtex" in pub:
                    pub.pop("copy_bibtex", None)
                    removed += 1
                print(f"::warning::{title}: {exc}")

    PUBLICATIONS_PATH.write_text(
        yaml.safe_dump(pubs, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )
    print(f"Refreshed {refreshed} citation(s); removed {removed} stale citation(s).")


if __name__ == "__main__":
    main()
