"""Convert pamphlet PDFs into provenance-stamped .txt files for the knowledge wiki.

Three-tier pipeline, cheapest first; each PDF stops at the first tier that
produces enough text:

  1. docling, default OCR            (local, free)
  2. docling, EasyOCR --force-ocr    (local, free, slower)
  3. Claude vision (normalize_pdf)   (API tokens -- only when both local passes fail)

A pass "fails" when the cleaned text comes out under MIN_CHARS: photographed
pamphlets that OCR well yield 2-5 KB per sheet, so a result far below that
means the engine skipped most of the page.

Usage (from the project root, with the project .venv active):
    python3 convert_pamphlets.py                    # my_pamphlets/ -> pamphlet_corpus/
    python3 convert_pamphlets.py src_dir out_dir    # explicit folders
    python3 convert_pamphlets.py --force            # redo files whose .txt already exists

Requires the docling venv at ~/.venvs/docling (tiers 1-2) and, for tier 3 only,
ANTHROPIC_API_KEY (or another credential the SDK resolves).
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

DOCLING = Path.home() / ".venvs" / "docling" / "bin" / "docling"
MIN_CHARS = 2500  # per PDF; below this a pass is considered failed
STAMP = "photographed by the analyst, November 2026"


def clean(text: str) -> str:
    """Strip embedded images and fix the OCR confusions these pamphlets hit."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = "\n".join(l for l in text.splitlines() if "base64" not in l)
    text = re.sub(r"\bAl\b", "AI", text)
    text = re.sub(r"\bAls\b", "AIs", text)
    text = text.replace("&amp;", "&")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def run_docling(pdf: Path, extra_args: list[str]) -> str | None:
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [str(DOCLING), str(pdf), "--to", "md", "--output", tmp, *extra_args]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"    docling failed: {res.stderr.strip()[-200:]}")
            return None
        md = Path(tmp) / f"{pdf.stem}.md"
        return clean(md.read_text(encoding="utf-8")) if md.exists() else None


def run_claude_vision(pdf: Path) -> str:
    import anthropic
    from utilities import normalize_pdf

    client = anthropic.Anthropic()
    model = os.environ.get("COOKBOOK_MODEL", "claude-haiku-5-5")
    return clean(normalize_pdf(client, str(pdf), model))


def convert(pdf: Path) -> tuple[str, str]:
    """Return (text, method) via the first tier that yields enough text."""
    print("  tier 1: docling default OCR...")
    text = run_docling(pdf, [])
    if text and len(text) >= MIN_CHARS:
        return text, "local OCR (docling)"

    print(f"    thin result ({len(text or '')} chars < {MIN_CHARS}); escalating")
    print("  tier 2: docling EasyOCR, full-page...")
    v2 = run_docling(pdf, ["--ocr-engine", "easyocr", "--force-ocr"])
    best = max(filter(None, [text, v2, ""]), key=len)
    if len(best) >= MIN_CHARS:
        return best, "local OCR (docling/EasyOCR)"

    print(f"    still thin ({len(best)} chars); escalating")
    print("  tier 3: Claude vision (uses API tokens)...")
    v3 = run_claude_vision(pdf)
    return (v3, "Claude vision") if len(v3) > len(best) else (best, "local OCR (docling)")


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv
    src = Path(args[0]) if args else Path("my_pamphlets")
    out = Path(args[1]) if len(args) > 1 else Path("pamphlet_corpus")
    out.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(src.glob("*.pdf"))
    if not pdfs:
        sys.exit(f"no PDFs in {src}/")

    for pdf in pdfs:
        dest = out / f"{pdf.stem}.txt"
        if dest.exists() and not force:
            print(f"{pdf.name}: {dest.name} exists, skipping (--force to redo)")
            continue
        print(f"{pdf.name}:")
        text, method = convert(pdf)
        title = pdf.stem.replace("_", " ")
        header = (
            f"[SOURCE: {title} pamphlet, {STAMP}. Transcribed via {method}; "
            f"OCR errors possible, figures should be treated as approximate.]"
        )
        dest.write_text(header + "\n\n" + text, encoding="utf-8")
        print(f"  -> {dest} ({len(text)} chars, {method})")


if __name__ == "__main__":
    main()
