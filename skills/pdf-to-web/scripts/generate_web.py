#!/usr/bin/env python3
"""
Save the academic website HTML to disk.

Usage:
    python generate_web.py \
        --html-file /tmp/website.html \
        --title "Paper Title" \
        --out-dir ./web/<pdf_name>/

The file is saved as:  <out-dir>/index.html
"""

import argparse
import os
import shutil


def save_web(html_file: str, title: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, "index.html")
    shutil.copy(html_file, dst)
    return os.path.abspath(dst)


def main():
    parser = argparse.ArgumentParser(description="Save the academic website HTML.")
    parser.add_argument(
        "--html-file", required=True, help="Path to the generated HTML file"
    )
    parser.add_argument("--title", default="Paper", help="Title of the paper")
    parser.add_argument("--out-dir", default="./web_output", help="Output directory")
    args = parser.parse_args()

    dst = save_web(args.html_file, args.title, args.out_dir)
    print(f"✅ 已生成《{args.title}》论文主页 → {dst}")


if __name__ == "__main__":
    main()
