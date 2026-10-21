#!/usr/bin/env python3
"""
IR 文档获取 + PDF 关键页面提取

功能：
  1. 给 URL → 下载 PDF
  2. PDF 每页转 PNG
  3. 启发式筛选图表密集页（跳过纯文字页和封面/法律页）
  4. 输出筛选后的 PNG 列表，供模型视觉查看

用法：
  python3 fetch_ir.py --url "https://example.com/report.pdf" --output-dir ./ir_output
  python3 fetch_ir.py --file ./local_report.pdf --output-dir ./ir_output

依赖：
  pip3 install pymupdf
"""

import argparse
import ipaddress
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request
from urllib.parse import unquote, urlparse

try:
    import fitz  # pymupdf
except ImportError:
    print("❌ 需要安装 pymupdf: pip3 install pymupdf", file=sys.stderr)
    sys.exit(1)


def _is_public_url(url: str) -> tuple[bool, str]:
    """Validate URL is http/https and not localhost/private network target.

    Defense against parser-differential SSRF (e.g. "http://127.0.0.1\\@1.1.1.1",
    where urllib.parse sees host 1.1.1.1 but urllib.request connects to
    127.0.0.1): URLs containing characters that the two parsers may treat
    differently are rejected outright, and the hostname must resolve
    exclusively to public IPs.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False, "Only http/https URLs are supported"

        disallowed = re.compile(r"[\\\t\n\r\f\v \x00-\x1f\x7f]")
        if disallowed.search(url) or disallowed.search(unquote(url)):
            return False, "URL contains disallowed control or whitespace characters"

        host = parsed.hostname
        if not host:
            return False, "Invalid URL host"

        host_l = host.lower()
        if host_l in {"localhost", "127.0.0.1", "::1"}:
            return False, "Localhost URLs are not allowed"

        if host_l != host_l.rstrip("."):
            return False, "URL host contains a trailing dot"

        infos = socket.getaddrinfo(host, None)
        for info in infos:
            ip_str = info[4][0]
            ip = ipaddress.ip_address(ip_str)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                return False, f"URL resolves to non-public IP: {ip}"
        return True, ""
    except Exception as e:
        return False, f"URL validation failed: {e}"


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-validates every redirect hop against SSRF rules."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        ok, reason = _is_public_url(newurl)
        if not ok:
            raise urllib.error.URLError(
                f"Redirect blocked for security reasons: {reason}"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_pdf(url: str, output_path: str, timeout: int = 30) -> bool:
    """下载 PDF 文件"""
    ok, reason = _is_public_url(url)
    if not ok:
        print(f"  ❌ 已拒绝 URL: {reason}", file=sys.stderr)
        return False
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
        )
        opener = urllib.request.build_opener(_SafeRedirectHandler)
        resp = opener.open(req, timeout=timeout)
        with open(output_path, "wb") as f:
            f.write(resp.read())
        size_mb = os.path.getsize(output_path) / 1e6
        print(f"  ✅ 下载完成: {size_mb:.1f} MB")
        return True
    except Exception as e:
        print(f"  ❌ 下载失败: {e}", file=sys.stderr)
        return False


def pdf_to_pages(pdf_path: str, output_dir: str, dpi: int = 200) -> list[dict]:
    """
    PDF 每页转 PNG，同时分析每页的图表密度。
    返回每页的元信息列表。
    """
    doc = fitz.open(pdf_path)
    total = len(doc)
    print(f"  📄 PDF 共 {total} 页，正在转换...")

    pages = []
    for i in range(total):
        page = doc[i]

        # 转 PNG
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        png_path = os.path.join(output_dir, f"page_{i+1:03d}.png")
        pix.save(png_path)

        # 分析页面特征
        text = page.get_text()
        text_len = len(text.strip())
        images = page.get_images(full=True)
        image_count = len(images)

        # 检测绘图对象（矢量图表通常以 drawing 形式存在）
        drawings = page.get_drawings()
        drawing_count = len(drawings)

        # 页面尺寸
        rect = page.rect
        page_area = rect.width * rect.height

        # 启发式：图表密度评分
        # 图片多 or 矢量绘图多 → 可能是图表页
        # 文字极少 → 可能是封面/分隔页（排除）
        # 文字极多且无图 → 纯文字页（排除）
        chart_score = 0

        if image_count >= 1:
            chart_score += 3 * min(image_count, 5)
        if drawing_count >= 10:
            chart_score += min(drawing_count / 10, 5)
        if 50 < text_len < 500:
            chart_score += 2  # 适量文字+图，典型图表页
        if text_len < 20:
            chart_score -= 3  # 几乎无文字，可能是封面或空白页
        if text_len > 2000 and image_count == 0:
            chart_score -= 3  # 纯文字页

        # 跳过第一页（通常是封面）和最后两页（通常是免责声明）
        if i == 0:
            chart_score -= 2
        if i >= total - 2:
            chart_score -= 2

        pages.append(
            {
                "page_num": i + 1,
                "png_path": png_path,
                "text_length": text_len,
                "image_count": image_count,
                "drawing_count": drawing_count,
                "chart_score": round(chart_score, 1),
                "first_50_chars": text[:50].replace("\n", " ").strip(),
            }
        )

    doc.close()
    return pages


def select_key_pages(pages: list[dict], max_pages: int = 8) -> list[dict]:
    """
    从所有页面中筛选出最可能包含图表的 N 页。
    按 chart_score 降序排列，取前 max_pages 页，然后按页码重新排序。
    """
    # 过滤掉明显的非图表页
    candidates = [p for p in pages if p["chart_score"] > 0]

    # 如果筛选后不够，放宽条件
    if len(candidates) < 3:
        candidates = [p for p in pages if p["chart_score"] > -2]

    # 按 chart_score 降序取前 N
    candidates.sort(key=lambda x: x["chart_score"], reverse=True)
    selected = candidates[:max_pages]

    # 按页码重新排序（方便阅读）
    selected.sort(key=lambda x: x["page_num"])

    return selected


def main():
    parser = argparse.ArgumentParser(description="IR 文档获取 + 关键页面提取")
    parser.add_argument("--url", type=str, help="PDF 下载 URL")
    parser.add_argument("--file", type=str, help="本地 PDF 文件路径")
    parser.add_argument("--output-dir", default="./ir_output", help="输出目录")
    parser.add_argument(
        "--max-pages", type=int, default=8, help="最多提取几页关键图表页"
    )
    parser.add_argument("--dpi", type=int, default=200, help="图片分辨率")
    args = parser.parse_args()

    if not args.url and not args.file:
        print("❌ 必须提供 --url 或 --file 参数", file=sys.stderr)
        sys.exit(1)

    out = args.output_dir
    os.makedirs(out, exist_ok=True)

    # Step 1: 获取 PDF
    if args.url:
        pdf_path = os.path.join(out, "report.pdf")
        print(f"📥 下载 PDF: {args.url[:80]}...")
        if not download_pdf(args.url, pdf_path):
            sys.exit(1)
    else:
        pdf_path = args.file
        if not os.path.exists(pdf_path):
            print(f"❌ 文件不存在: {pdf_path}", file=sys.stderr)
            sys.exit(1)

    # Step 2: 转换所有页面
    all_pages = pdf_to_pages(pdf_path, out, dpi=args.dpi)

    # Step 3: 筛选关键图表页
    key_pages = select_key_pages(all_pages, max_pages=args.max_pages)

    # Step 4: 保存结果
    result = {
        "pdf_path": pdf_path,
        "total_pages": len(all_pages),
        "selected_count": len(key_pages),
        "selected_pages": key_pages,
        "all_pages_summary": [
            {
                "page": p["page_num"],
                "score": p["chart_score"],
                "preview": p["first_50_chars"][:30],
            }
            for p in all_pages
        ],
    }

    json_path = os.path.join(out, "ir_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    # Step 5: 打印结果
    print(f"\n✅ 完成! 共 {len(all_pages)} 页，筛选出 {len(key_pages)} 页关键图表页：")
    print()
    for p in key_pages:
        print(f"  📊 第{p['page_num']}页 (score={p['chart_score']}) → {p['png_path']}")
        print(
            f"     {p['image_count']}张图片, {p['drawing_count']}个绘图对象, {p['text_length']}字符"
        )
        if p["first_50_chars"]:
            print(f"     开头: {p['first_50_chars'][:40]}...")
        print()

    print(f"请查看以上 PNG 文件进行视觉分析。")
    print(f"如需查看全部页面，PNG 文件在 {out}/ 目录下。")


if __name__ == "__main__":
    main()
