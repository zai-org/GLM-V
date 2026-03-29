#!/usr/bin/env python3
"""
Save a slide HTML file and optionally generate the index.html navigation page.

Usage:
    python generate_slide.py \
        --html-file /tmp/slide.html \
        --index 3 --total 12 \
        --title "My Presentation" \
        --out-dir ./ppt/<pdf_name>/

The slide is saved as:  <out-dir>/slide_<index:02d>.html
When index == total, an index.html with slide navigation is auto-generated.
"""

import argparse
import os
import shutil


def save_slide(html_file: str, index: int, total: int, title: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, f"slide_{index:02d}.html")
    shutil.copy(html_file, dst)
    return os.path.abspath(dst)


def generate_index(total: int, title: str, out_dir: str) -> str:
    """Generate index.html with navigation links to all slides."""
    slides_html = []
    for i in range(1, total + 1):
        slides_html.append(
            f'<a href="slide_{i:02d}.html" class="slide-link">'
            f'<span class="num">{i}</span>'
            f"</a>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Slides</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;color:#1a1a2e;display:flex;flex-direction:column;align-items:center;padding:60px 20px;min-height:100vh}}
h1{{font-size:1.8em;margin-bottom:8px;text-align:center}}
.subtitle{{color:#64748b;margin-bottom:40px;font-size:.95em}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:16px;max-width:800px;width:100%}}
.slide-link{{display:flex;align-items:center;justify-content:center;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:28px 20px;text-decoration:none;color:#1a1a2e;font-weight:600;font-size:1.3em;transition:all .2s;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.slide-link:hover{{background:#2563eb;color:#fff;transform:translateY(-3px);box-shadow:0 8px 25px rgba(37,99,235,.25)}}
.slide-link .num{{}}
.start{{margin-top:40px;display:inline-flex;align-items:center;gap:8px;padding:14px 36px;background:#2563eb;color:#fff;border-radius:10px;text-decoration:none;font-weight:600;font-size:1.05em;transition:all .2s}}
.start:hover{{background:#1d4ed8;transform:translateY(-2px);box-shadow:0 4px 12px rgba(37,99,235,.3)}}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="subtitle">Total {total} slides — click any slide to view, or start from the beginning</p>
<div class="grid">
{''.join(slides_html)}
</div>
<a href="slide_01.html" class="start">▶ Start Presentation</a>
</body>
</html>"""

    index_path = os.path.join(out_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    return os.path.abspath(index_path)


def main():
    parser = argparse.ArgumentParser(
        description="Save a slide HTML file and report progress."
    )
    parser.add_argument(
        "--html-file", required=True, help="Path to the rendered HTML file"
    )
    parser.add_argument("--index", type=int, required=True, help="1-based slide index")
    parser.add_argument("--total", type=int, required=True, help="Total slides")
    parser.add_argument("--title", default="Presentation", help="Presentation title")
    parser.add_argument("--out-dir", default="./slides_output", help="Output directory")
    args = parser.parse_args()

    dst = save_slide(args.html_file, args.index, args.total, args.title, args.out_dir)

    if args.index < args.total:
        print(f"[{args.index}/{args.total}] 已保存第 {args.index} 页 → {dst}")
        print(f"请继续生成第 {args.index + 1} 页。")
    else:
        print(f"[{args.index}/{args.total}] 已保存第 {args.index} 页 → {dst}")
        idx = generate_index(args.total, args.title, args.out_dir)
        print(f"✅ 《{args.title}》全部 {args.total} 页 PPT 生成完成！")
        print(f"📂 输出目录：{os.path.abspath(args.out_dir)}")
        print(f"🏠 导航页：{idx}")


if __name__ == "__main__":
    main()
