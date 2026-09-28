#!/usr/bin/env python3
"""
Generate publication teaser images.

Policy:
- For papers with a curated crop in _data/publications_config.json, generate the
  final teaser automatically from that crop every time the workflow runs.
- For a newly selected paper without a curated crop, automatically extract up to
  three candidate figure crops. Nothing is promoted to the homepage until one
  candidate/crop is chosen once.

This keeps the homepage stable while removing the repetitive PDF/image work.
"""

from __future__ import annotations

import io
import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import fitz  # PyMuPDF
import yaml
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "_data" / "publications_config.json"
PUBLICATIONS_PATH = ROOT / "_data" / "publications.yml"
ASSET_DIR = ROOT / "assets" / "img" / "publications"
CANDIDATE_DIR = ASSET_DIR / "candidates"

USER_AGENT = (
    "Mozilla/5.0 (compatible; academic-homepage-teaser-sync/1.0; "
    "+https://github.com/liuzhouyang/liuzhouyang.github.io)"
)


def normalize_title(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def slugify(title: str) -> str:
    s = normalize_title(title).replace(" ", "-")
    return s[:72].strip("-") or "paper"


def fetch(url: str, attempts: int = 3) -> bytes:
    last = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/pdf,*/*",
                },
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = resp.read()
            if len(data) < 1000:
                raise RuntimeError("downloaded file is unexpectedly small")
            return data
        except Exception as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to download {url}: {last}")


def to_pdf_url(url: str) -> str:
    if "arxiv.org/abs/" in url:
        return url.replace("arxiv.org/abs/", "arxiv.org/pdf/")
    return url


def trim_white(image: Image.Image, padding: int = 12) -> Image.Image:
    """Trim near-white outer margins while preserving a little breathing room."""
    rgb = image.convert("RGB")
    # Treat pixels darker than 248 in any channel as content.
    gray = rgb.convert("L")
    mask = gray.point(lambda p: 255 if p < 248 else 0)
    bbox = mask.getbbox()
    if not bbox:
        return rgb

    left, top, right, bottom = bbox
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(rgb.width, right + padding)
    bottom = min(rgb.height, bottom + padding)
    return rgb.crop((left, top, right, bottom))


def render_crop(
    pdf_bytes: bytes,
    page_index: int,
    crop_norm: list[float],
    output: Path,
    zoom: float = 2.6,
) -> None:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if page_index < 0 or page_index >= len(doc):
        raise IndexError(f"page {page_index} out of range for {len(doc)}-page PDF")
    page = doc[page_index]
    r = page.rect
    x0, y0, x1, y1 = crop_norm
    clip = fitz.Rect(r.x0 + x0 * r.width, r.y0 + y0 * r.height,
                     r.x0 + x1 * r.width, r.y0 + y1 * r.height)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    img = trim_white(img)

    # Avoid huge repository images.
    if img.width > 1500:
        new_h = round(img.height * 1500 / img.width)
        img = img.resize((1500, new_h), Image.Resampling.LANCZOS)

    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(output, "PNG", optimize=True)


CAPTION_RE = re.compile(r"\b(?:Fig\.|Figure)\s*([0-9]+)", re.I)


def caption_candidates(pdf_bytes: bytes, max_candidates: int = 3):
    """Yield heuristic crops above figure captions for a new/unconfigured paper."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    found = []
    seen = set()

    for page_index, page in enumerate(doc):
        if page_index > 7:  # Homepage teasers are usually in the early paper.
            break
        W, H = page.rect.width, page.rect.height

        blocks = page.get_text("blocks")
        for block in blocks:
            x0, y0, x1, y1, text = block[:5]
            m = CAPTION_RE.search(text or "")
            if not m:
                continue
            fig_no = int(m.group(1))
            if fig_no in seen:
                continue
            seen.add(fig_no)

            cx = (x0 + x1) / 2
            width = x1 - x0

            # Estimate single-column vs two-column figure position.
            if width > 0.55 * W or (x0 < 0.28 * W and x1 > 0.72 * W):
                fx0, fx1 = 0.06, 0.94
                crop_h = 0.28
            elif cx < W / 2:
                fx0, fx1 = 0.055, 0.495
                crop_h = 0.23
            else:
                fx0, fx1 = 0.505, 0.945
                crop_h = 0.23

            fy1 = max(0.08, y0 / H - 0.008)
            fy0 = max(0.035, fy1 - crop_h)
            if fy1 - fy0 < 0.06:
                continue

            found.append((fig_no, page_index, [fx0, fy0, fx1, fy1]))
            if len(found) >= max_candidates:
                return found
    return found


def load_publications() -> list[dict]:
    if not PUBLICATIONS_PATH.exists():
        return []
    data = yaml.safe_load(PUBLICATIONS_PATH.read_text(encoding="utf-8"))
    return data or []


def source_for_publication(pub: dict, teaser_cfg: dict | None) -> str:
    if teaser_cfg and teaser_cfg.get("source"):
        return teaser_cfg["source"]
    for field in ("pdf", "paper"):
        url = pub.get(field)
        if url:
            return to_pdf_url(str(url))
    return ""


def main() -> None:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    publications = load_publications()
    teaser_cfgs = {
        normalize_title(title): value
        for title, value in cfg.get("teasers", {}).items()
    }

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)

    for pub in publications:
        title = str(pub.get("title", "")).strip()
        if not title:
            continue
        norm = normalize_title(title)
        teaser_cfg = teaser_cfgs.get(norm)
        source = source_for_publication(pub, teaser_cfg)
        if not source:
            print(f"Skip teaser for {title}: no PDF source", file=sys.stderr)
            continue

        try:
            pdf = fetch(source)
        except Exception as exc:
            print(f"Warning: could not fetch teaser PDF for {title}: {exc}", file=sys.stderr)
            continue

        if teaser_cfg and teaser_cfg.get("crop") is not None:
            image_path = teaser_cfg.get("image") or pub.get("image")
            if not image_path:
                print(f"Skip curated teaser for {title}: no image path", file=sys.stderr)
                continue
            target = ROOT / str(image_path).lstrip("/")
            try:
                render_crop(
                    pdf,
                    int(teaser_cfg.get("page", 0)),
                    [float(v) for v in teaser_cfg["crop"]],
                    target,
                )
                print(
                    f"Generated curated teaser: {target.relative_to(ROOT)} "
                    f"({teaser_cfg.get('figure', 'manual crop')})"
                )
            except Exception as exc:
                print(f"Warning: teaser render failed for {title}: {exc}", file=sys.stderr)
            continue

        # New selected publication: produce candidates, but do not change the homepage.
        slug = slugify(title)
        out_dir = CANDIDATE_DIR / slug
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        candidates = caption_candidates(pdf, max_candidates=3)
        for fig_no, page_index, crop in candidates:
            target = out_dir / f"fig-{fig_no}.png"
            try:
                render_crop(pdf, page_index, crop, target, zoom=2.2)
            except Exception as exc:
                print(f"Warning: candidate render failed for {title} Fig. {fig_no}: {exc}", file=sys.stderr)

        if candidates:
            print(f"Generated {len(candidates)} teaser candidates for new paper: {title}")
        else:
            print(f"No figure-caption candidates found for: {title}", file=sys.stderr)


if __name__ == "__main__":
    main()
