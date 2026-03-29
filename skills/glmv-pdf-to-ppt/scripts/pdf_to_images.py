#!/usr/bin/env python3
"""
Convert a local PDF file to PNG images.
Use curl to download remote PDFs before calling this script.

Usage:
    python pdf_to_images.py <pdf_path> [--dpi 120] [--out-dir DIR]

Output (stdout):
    JSON list of {"page": int, "path": "/abs/path/page_001.png"}
"""

import os
import sys
import json
import argparse
import tempfile


def convert_pdf(pdf_path: str, out_dir: str, dpi: int) -> list[dict]:
    try:
        import fitz
    except ImportError:
        print(
            "[ERROR] PyMuPDF (fitz) not installed. Run: pip install pymupdf",
            file=sys.stderr,
        )
        sys.exit(1)

    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    results = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        filename = f"page_{page_num + 1:03d}.png"
        out_path = os.path.join(out_dir, filename)
        pix.save(out_path)
        results.append({"page": page_num + 1, "path": os.path.abspath(out_path)})
        print(f"  page {page_num + 1}/{len(doc)} → {out_path}", file=sys.stderr)

    doc.close()
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF pages to local PNG images."
    )
    parser.add_argument("pdf_source", help="Local path to the PDF file.")
    parser.add_argument(
        "--dpi", type=int, default=120, help="Rendering DPI (default 120)."
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Directory to save images (default: temp dir named after PDF stem).",
    )
    args = parser.parse_args()

    source = args.pdf_source
    if not os.path.isfile(source):
        print(f"[ERROR] File not found: {source}", file=sys.stderr)
        sys.exit(1)
    pdf_path = source
    pdf_stem = os.path.splitext(os.path.basename(source))[0]
    out_dir = args.out_dir or os.path.join(tempfile.gettempdir(), f"{pdf_stem}_pages")
    results = convert_pdf(pdf_path, out_dir, args.dpi)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
