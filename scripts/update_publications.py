#!/usr/bin/env python3
"""
Refresh _data/publications.yml for a Minimal Light academic homepage.

Sources:
  - DBLP person XML: bibliographic metadata
  - GitHub public repositories: optional code-link discovery
  - _data/publications_config.json: pinned works, manual accepted papers,
    and a few human-curated overrides.

The homepage remains curated:
  * signature papers stay pinned;
  * remaining slots are filled by the newest relevant papers;
  * arXiv/extended-abstract duplicates are suppressed;
  * metadata is refreshed automatically.
"""

from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "_data" / "publications_config.json"
OUTPUT_PATH = ROOT / "_data" / "publications.yml"

USER_AGENT = "academic-homepage-publication-sync/1.0 (+https://github.com/liuzhouyang/liuzhouyang.github.io)"


def fetch(url: str, *, attempts: int = 3) -> bytes:
    last_error = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/xml, application/json, text/plain, */*",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def text_of(node, tag: str) -> str:
    child = node.find(tag)
    if child is None:
        return ""
    return "".join(child.itertext()).strip()


def all_text(node, tag: str) -> list[str]:
    out = []
    for child in node.findall(tag):
        value = "".join(child.itertext()).strip()
        if value:
            out.append(value)
    return out


def normalize_title(title: str) -> str:
    s = html.unescape(title).lower()
    s = re.sub(r"\(extended abstract\)", "", s, flags=re.I)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def yaml_quote(value) -> str:
    # JSON strings are valid YAML scalars and save us from an extra dependency.
    return json.dumps(str(value), ensure_ascii=False)


def parse_year(value: str) -> int:
    m = re.search(r"\d{4}", value or "")
    return int(m.group(0)) if m else 0


def is_preprint(record: dict) -> bool:
    key = record.get("dblp_key", "")
    venue = record.get("venue_raw", "")
    return key.startswith("journals/corr/") or venue == "CoRR"


def record_quality(record: dict) -> tuple:
    # Prefer a peer-reviewed/final record over CoRR for the same title.
    return (
        0 if is_preprint(record) else 1,
        1 if record.get("paper") else 0,
        1 if record.get("dblp_key") else 0,
    )


def parse_dblp(xml_bytes: bytes, cfg: dict) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    out = []

    allowed = {"article", "inproceedings", "proceedings", "incollection"}
    for r in root.findall(".//r"):
        children = list(r)
        if not children:
            continue
        pub = children[0]
        if pub.tag not in allowed:
            continue

        title = text_of(pub, "title").rstrip(".")
        if not title:
            continue
        if any(x.lower() in title.lower() for x in cfg.get("exclude_title_contains", [])):
            continue

        authors = all_text(pub, "author")
        year = parse_year(text_of(pub, "year"))
        journal = text_of(pub, "journal")
        booktitle = text_of(pub, "booktitle")
        venue_raw = journal or booktitle or "Preprint"
        ee = all_text(pub, "ee")
        key = pub.attrib.get("key", "")
        pages = text_of(pub, "pages")

        # Prefer an arXiv URL when DBLP explicitly points to one; otherwise use the first EE.
        paper = ""
        for link in ee:
            if "arxiv.org" in link.lower():
                paper = link
                break
        if not paper and ee:
            paper = ee[0]

        out.append(
            {
                "title": title,
                "authors_list": authors,
                "year": year,
                "date": f"{year:04d}-01" if year else "0000-01",
                "venue_raw": venue_raw,
                "venue": cfg.get("venue_shortcuts", {}).get(venue_raw, venue_raw),
                "pages": pages,
                "paper": paper,
                "dblp_key": key,
                "dblp": f"https://dblp.org/rec/{key}" if key else "",
                "bibtex": f"https://dblp.org/rec/{key}.bib" if key else "",
            }
        )
    return out


def merge_same_titles(records: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for r in records:
        grouped.setdefault(normalize_title(r["title"]), []).append(r)

    merged = []
    for _, items in grouped.items():
        items.sort(key=record_quality, reverse=True)
        best = dict(items[0])

        # Keep an arXiv link from a duplicate preprint when the final record only has a DOI.
        arxiv = ""
        for item in items:
            link = item.get("paper", "")
            if "arxiv.org" in link.lower():
                arxiv = link
                break
        if arxiv:
            best["paper"] = arxiv

        merged.append(best)
    return merged


def apply_manual_and_overrides(records: list[dict], cfg: dict) -> list[dict]:
    by_norm = {normalize_title(r["title"]): r for r in records}

    # Manual records let newly accepted papers appear before DBLP has indexed the final venue.
    for manual in cfg.get("manual_records", []):
        norm = normalize_title(manual["title"])
        if norm not in by_norm:
            r = {
                "title": manual["title"],
                "authors_list": manual.get("authors", []),
                "year": int(manual.get("year", 0)),
                "date": manual.get("date", f'{manual.get("year", 0):04d}-01'),
                "venue_raw": manual.get("venue", "Preprint"),
                "venue": manual.get("venue", "Preprint"),
                "pages": "",
                "paper": manual.get("paper", ""),
                "code": manual.get("code", ""),
                "dblp_key": "",
                "dblp": "",
                "bibtex": "",
                "short_title": manual.get("short_title", ""),
            }
            by_norm[norm] = r
        else:
            r = by_norm[norm]
            # If DBLP still only has a CoRR record, keep the known accepted venue.
            if is_preprint(r) and manual.get("venue"):
                r["venue"] = manual["venue"]
            for field in ("paper", "code", "date", "short_title"):
                if manual.get(field):
                    r[field] = manual[field]

    overrides = cfg.get("overrides", {})
    for title, values in overrides.items():
        norm = normalize_title(title)
        if norm in by_norm:
            by_norm[norm].update(values)

    return list(by_norm.values())



def apply_teaser_paths(records: list[dict], cfg: dict) -> list[dict]:
    """Attach teaser paths only when the image file actually exists.

    This prevents broken-image placeholders on a fresh clone or when a remote
    PDF cannot be downloaded during a workflow run.
    """
    by_norm = {normalize_title(r["title"]): r for r in records}
    for title, teaser in cfg.get("teasers", {}).items():
        r = by_norm.get(normalize_title(title))
        image_path = teaser.get("image", "")
        if not r or not image_path:
            continue
        local_path = ROOT / image_path.lstrip("/")
        if local_path.exists():
            r["image"] = image_path
        else:
            r.pop("image", None)
    return records


def discover_github_repos(cfg: dict) -> list[dict]:
    user = cfg.get("github_user")
    if not user:
        return []
    try:
        data = fetch(f"https://api.github.com/users/{user}/repos?per_page=100&sort=updated")
        return json.loads(data.decode("utf-8"))
    except Exception as exc:
        print(f"Warning: GitHub repo discovery skipped: {exc}", file=sys.stderr)
        return []


def token_set(s: str) -> set[str]:
    stop = {
        "a", "an", "the", "for", "of", "with", "and", "to", "via", "on",
        "in", "from", "using", "efficient", "learning", "framework"
    }
    return {x for x in normalize_title(s).split() if len(x) > 2 and x not in stop}


def attach_code_links(records: list[dict], repos: list[dict]) -> None:
    for r in records:
        if r.get("code"):
            continue
        title_tokens = token_set(r["title"])
        if not title_tokens:
            continue

        best_score = 0.0
        best_url = ""
        for repo in repos:
            hay = f'{repo.get("name", "")} {repo.get("description") or ""}'
            repo_tokens = token_set(hay)
            if not repo_tokens:
                continue
            overlap = len(title_tokens & repo_tokens)
            score = overlap / max(1, min(len(title_tokens), 8))
            if score > best_score:
                best_score = score
                best_url = repo.get("html_url", "")

        if best_score >= 0.50:
            r["code"] = best_url


def author_rank(record: dict, author_name: str) -> int:
    names = record.get("authors_list", [])
    try:
        return names.index(author_name) + 1
    except ValueError:
        return 999


def relevant_for_autofill(record: dict, cfg: dict) -> bool:
    text = normalize_title(record.get("title", ""))
    return any(normalize_title(k) in text for k in cfg.get("auto_keywords", []))


def find_by_title(records: list[dict], wanted: str):
    wn = normalize_title(wanted)
    exact = [r for r in records if normalize_title(r["title"]) == wn]
    if exact:
        return exact[0]
    # Tolerate minor title capitalization/punctuation differences.
    fuzzy = [r for r in records if wn in normalize_title(r["title"]) or normalize_title(r["title"]) in wn]
    return fuzzy[0] if fuzzy else None


def select_records(records: list[dict], cfg: dict) -> list[dict]:
    selected = []
    seen = set()

    # Signature works stay on the homepage.
    for title in cfg.get("pinned_titles", []):
        r = find_by_title(records, title)
        if r:
            n = normalize_title(r["title"])
            if n not in seen:
                selected.append(r)
                seen.add(n)

    # Remaining slots track current work automatically.
    candidates = [
        r for r in records
        if normalize_title(r["title"]) not in seen and relevant_for_autofill(r, cfg)
    ]
    candidates.sort(
        key=lambda r: (
            r.get("date", f'{r.get("year", 0):04d}-01'),
            r.get("year", 0),
            -author_rank(r, cfg.get("author_name", "")),
            0 if is_preprint(r) else 1,
        ),
        reverse=True,
    )

    for r in candidates:
        if len(selected) >= int(cfg.get("max_items", 6)):
            break
        n = normalize_title(r["title"])
        if n not in seen:
            selected.append(r)
            seen.add(n)

    # If relevant filtering yields fewer than max_items, fill from recent non-extended records.
    if len(selected) < int(cfg.get("max_items", 6)):
        fallback = sorted(
            [r for r in records if normalize_title(r["title"]) not in seen],
            key=lambda r: (
                r.get("date", f'{r.get("year", 0):04d}-01'),
                r.get("year", 0),
                -author_rank(r, cfg.get("author_name", "")),
            ),
            reverse=True,
        )
        for r in fallback:
            if len(selected) >= int(cfg.get("max_items", 6)):
                break
            n = normalize_title(r["title"])
            if n not in seen:
                selected.append(r)
                seen.add(n)

    # Display newest first, while preserving deterministic order.
    selected.sort(
        key=lambda r: (r.get("date", f'{r.get("year", 0):04d}-01'), r.get("title", "")),
        reverse=True,
    )
    return selected[: int(cfg.get("max_items", 6))]


def render_authors(names: list[str], me: str) -> str:
    parts = []
    for name in names:
        if name == me:
            parts.append(f"<strong>{html.escape(name)}</strong>")
        else:
            parts.append(html.escape(name))
    return ", ".join(parts)



def fetch_bibtex_text(record: dict) -> str:
    """Fetch the exact DBLP BibTeX export and store it for inline display."""
    url = record.get("bibtex", "")
    if not url:
        return ""
    try:
        data = fetch(url)
        return data.decode("utf-8", errors="replace").strip()
    except Exception as exc:
        print(
            f"Warning: could not fetch BibTeX for {record.get('title', '')}: {exc}",
            file=sys.stderr,
        )
        return ""


def write_yaml(records: list[dict], cfg: dict) -> None:
    lines = [
        "# AUTO-GENERATED by scripts/update_publications.py",
        "# Do not edit this file directly; edit _data/publications_config.json instead.",
        "",
    ]
    for r in records:
        lines.append(f"- title: {yaml_quote(r.get('title', ''))}")
        if r.get("short_title"):
            lines.append(f"  short_title: {yaml_quote(r['short_title'])}")
        lines.append(
            f"  authors: {yaml_quote(render_authors(r.get('authors_list', []), cfg.get('author_name', '')))}"
        )
        lines.append(f"  conference_short: {yaml_quote(r.get('venue', ''))}")
        venue_line = r.get("venue", "")
        if r.get("pages"):
            venue_line += f", pp. {r['pages']}"
        lines.append(f"  conference: {yaml_quote(venue_line)}")
        lines.append(f"  year: {int(r.get('year', 0))}")
        if r.get("paper"):
            lines.append(f"  pdf: {yaml_quote(r['paper'])}")
        if r.get("code"):
            lines.append(f"  code: {yaml_quote(r['code'])}")
        if r.get("image"):
            lines.append(f"  image: {yaml_quote(r['image'])}")
        if r.get("dblp"):
            lines.append(f"  dblp: {yaml_quote(r['dblp'])}")
        bibtex_text = r.get("bibtex_text", "")
        if bibtex_text:
            # YAML block scalar keeps the full BibTeX human-readable and copyable.
            lines.append("  bibtex_text: |")
            for bib_line in bibtex_text.splitlines():
                lines.append(f"    {bib_line}")
        lines.append("")
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    pid = cfg["dblp_pid"]

    xml_data = fetch(f"https://dblp.org/pid/{pid}.xml")
    records = parse_dblp(xml_data, cfg)
    records = merge_same_titles(records)
    records = apply_manual_and_overrides(records, cfg)
    records = apply_teaser_paths(records, cfg)

    repos = discover_github_repos(cfg)
    attach_code_links(records, repos)

    selected = select_records(records, cfg)
    if not selected:
        raise RuntimeError("No publications were selected; refusing to overwrite output.")

    for record in selected:
        record["bibtex_text"] = fetch_bibtex_text(record)

    write_yaml(selected, cfg)
    print(f"Wrote {len(selected)} selected publications to {OUTPUT_PATH.relative_to(ROOT)}")
    for r in selected:
        print(f"  - {r.get('year')}: {r.get('title')}")


if __name__ == "__main__":
    main()
