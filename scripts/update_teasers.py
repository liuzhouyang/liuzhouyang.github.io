#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import sys
import time
import urllib.request
from pathlib import Path

import fitz
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "_data" / "publications_config.json"
PUBLICATIONS_PATH = ROOT / "_data" / "publications.yml"
USER_AGENT = "Mozilla/5.0 academic-homepage-teaser-sync/2.0"


def normalize_title(title: str) -> str:
    import re
    return " ".join(re.sub(r"[^a-z0-9]+", " ", title.lower()).split())


def fetch_pdf(urls: list[str]) -> bytes:
    errors = []
    for url in urls:
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*"},
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = resp.read()
                    ctype = (resp.headers.get("Content-Type") or "").lower()
                if not data.startswith(b"%PDF") or len(data) < 10000:
                    raise RuntimeError(
                        f"not a valid PDF: content-type={ctype}, bytes={len(data)}"
                    )
                return data
            except Exception as exc:
                errors.append(f"{url}: {exc}")
                if attempt < 2:
                    time.sleep(2 ** attempt)
    raise RuntimeError(" | ".join(errors))


def render_crop(pdf: bytes, page_index: int, crop: list[float], output: Path) -> None:
    doc = fitz.open(stream=pdf, filetype="pdf")
    if page_index < 0 or page_index >= len(doc):
        raise RuntimeError(f"page {page_index} out of range; PDF has {len(doc)} pages")

    page = doc[page_index]
    rect = page.rect
    x0, y0, x1, y1 = map(float, crop)
    clip = fitz.Rect(
        rect.x0 + x0 * rect.width,
        rect.y0 + y0 * rect.height,
        rect.x0 + x1 * rect.width,
        rect.y0 + y1 * rect.height,
    )
    pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0), clip=clip, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

    if img.width < 250 or img.height < 80:
        raise RuntimeError(f"suspicious teaser size: {img.size}")

    if img.width > 1600:
        new_h = round(img.height * 1600 / img.width)
        img = img.resize((1600, new_h), Image.Resampling.LANCZOS)

    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(output, "PNG", optimize=True)

    if output.stat().st_size < 5000:
        raise RuntimeError(f"suspiciously small output: {output.stat().st_size} bytes")


def source_list(teaser: dict) -> list[str]:
    sources = teaser.get("sources")
    if sources:
        return [str(x) for x in sources]

    source = str(teaser.get("source", ""))
    if "arxiv.org/abs/" in source:
        source = source.replace("arxiv.org/abs/", "arxiv.org/pdf/")
    if source:
        return [source]
    return []


def main() -> None:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    publications = yaml.safe_load(PUBLICATIONS_PATH.read_text(encoding="utf-8")) or []
    pubs = {normalize_title(p.get("title", "")): p for p in publications}

    failures = []
    generated = []

    for title, teaser in cfg.get("teasers", {}).items():
        norm = normalize_title(title)
        pub = pubs.get(norm)
        if pub is None:
            failures.append(f"{title}: selected publication missing from publications.yml")
            continue

        image_path = str(teaser["image"])
        output = ROOT / image_path.lstrip("/")
        urls = source_list(teaser)
        if not urls:
            failures.append(f"{title}: no PDF source configured")
            continue

        try:
            print(f"[teaser] {title}")
            pdf = fetch_pdf(urls)
            render_crop(pdf, int(teaser["page"]), teaser["crop"], output)
            pub["image"] = image_path
            generated.append(output)
            print(f"[teaser] OK: {output.relative_to(ROOT)} ({output.stat().st_size} bytes)")
        except Exception as exc:
            pub.pop("image", None)
            failures.append(f"{title}: {exc}")

    if failures:
        print("\nTEASER GENERATION FAILED:", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        raise SystemExit(1)

    expected = len(cfg.get("teasers", {}))
    if len(generated) != expected:
        raise SystemExit(f"Expected {expected} teasers, generated {len(generated)}")

    PUBLICATIONS_PATH.write_text(
        yaml.safe_dump(publications, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )
    print(f"Generated and registered {len(generated)} teaser images.")


if __name__ == "__main__":
    main()
