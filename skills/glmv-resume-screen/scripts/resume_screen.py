"""
GLM-V Resume Screening Tool
Batch-read and screen resumes with Zhipu GLM-V vision models.

Official API docs (https://docs.bigmodel.cn/api-reference/模型-api/对话补全):
- file_url supports URL only (no local path, no base64)
- Supported remote formats: pdf/doc/docx/txt, up to 50 files
- Local files support PDF only (automatically converted page-by-page into images)
- file_url cannot be mixed with image_url or video_url in the same request
"""

import os
import json
import base64
import argparse
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

import requests

try:
    import fitz  # PyMuPDF

    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

DEFAULT_MODEL = "glm-4.6v"
API_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# Model max_tokens limits (per official docs)
MODEL_MAX_TOKENS = {
    "glm-4.6v": {"default": 16384, "max": 32768},
    "glm-4.6v-flash": {"default": 16384, "max": 32768},
    "glm-4.6v-flashx": {"default": 16384, "max": 32768},
}

DEFAULT_SYSTEM_PROMPT = (
    "你是一位专业的人力资源专家和简历筛选助手。"
    "你需要仔细阅读每份简历，根据用户给出的筛选标准，判断每位候选人是否符合要求，并给出详细的分析原因。"
    "输出必须是严格的 Markdown 表格格式，表头为：序号、候选人姓名、是否符合、符合程度（高/中/低）、原因分析。"
    "原因分析应简明扼要，突出与筛选标准的匹配点和不足之处。"
)

DEFAULT_USER_PROMPT_TEMPLATE = (
    "以下是 {count} 份候选人的简历，请根据以下筛选标准进行评估：\n\n"
    "## 筛选标准\n{criteria}\n\n"
    "请逐一分析每份简历，并输出 Markdown 表格。"
)


def _is_url(s: str) -> bool:
    return s.strip().startswith(("http://", "https://"))


def _pdf_to_images(pdf_path: str) -> List[str]:
    """Convert local PDF pages to base64 data URLs."""
    if not HAS_PYMUPDF:
        raise RuntimeError(
            "PyMuPDF is required to process local PDF files. "
            "Install it with: pip install PyMuPDF"
        )
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF file: {pdf_path}")

    doc = fitz.open(str(path))
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        b64 = base64.b64encode(img_bytes).decode()
        images.append(f"data:image/png;base64,{b64}")
    doc.close()
    return images


def screen(
    files: List[str],
    criteria: str,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    system_prompt: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> Dict[str, Any]:
    """
    Screen resumes using GLM-V model.

    Args:
        files: Resume file URLs (pdf/docx/txt, URL only, max 50)
        criteria: Screening criteria text
        api_key: ZhiPu API Key
        model: Model name (default: glm-4.6v)
        system_prompt: Custom system prompt
        temperature: Sampling temperature (default: 0.3 for consistent evaluation)
        max_tokens: Max output tokens (default: 4096)

    Returns:
        Dict with success, result, and usage fields
    """
    # Validate max_tokens against model limits
    model_key = model.lower()
    model_limits = MODEL_MAX_TOKENS.get(model_key)
    if model_limits and max_tokens > model_limits["max"]:
        return {
            "success": False,
            "error": f"max_tokens {max_tokens} exceeds model '{model}' limit of {model_limits['max']}.",
        }

    if not api_key:
        api_key = os.environ.get("ZHIPU_API_KEY")

    if not api_key:
        return {
            "success": False,
            "error": (
                "ZHIPU_API_KEY not configured. "
                "Get your API key at: https://bigmodel.cn/usercenter/proj-mgmt/apikeys. "
                "未配置 ZHIPU_API_KEY，请在上述链接获取并配置。"
            ),
        }

    if not files:
        return {"success": False, "error": "No resume files provided."}

    if not criteria.strip():
        return {"success": False, "error": "Screening criteria cannot be empty."}

    if len(files) > 50:
        return {"success": False, "error": f"Too many files: {len(files)} (max 50)."}

    # Validate: local PDFs and remote URLs cannot mix (API limitation: file_url and image_url cannot coexist)
    has_local = any(not _is_url(f) for f in files)
    has_remote = any(_is_url(f) for f in files)
    if has_local and has_remote:
        return {
            "success": False,
            "error": "Cannot mix local files and URLs in the same request (API limitation). Use one or the other.",
        }

    if has_local:
        # All local PDFs → image_url (base64)
        local_page_count = 0
        pdf_page_images: List[List[str]] = []
        for f in files:
            path = Path(f.strip())
            if not path.exists():
                return {"success": False, "error": f"File not found: {f}"}
            if path.suffix.lower() != ".pdf":
                return {
                    "success": False,
                    "error": f"Local files only support PDF format: {f}",
                }
            try:
                pages = _pdf_to_images(str(path))
            except (ValueError, FileNotFoundError, RuntimeError) as e:
                return {"success": False, "error": str(e)}
            pdf_page_images.append(pages)
            local_page_count += len(pages)

        if local_page_count > 50:
            return {
                "success": False,
                "error": f"Too many pages: {local_page_count} (max 50).",
            }

        content = []
        for pages in pdf_page_images:
            for page_img in pages:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": page_img},
                    }
                )
    else:
        # All remote URLs → file_url
        if len(files) > 50:
            return {
                "success": False,
                "error": f"Too many files: {len(files)} (max 50).",
            }

        content = []
        for f in files:
            content.append(
                {
                    "type": "file_url",
                    "file_url": {"url": f.strip()},
                }
            )

    user_prompt = DEFAULT_USER_PROMPT_TEMPLATE.format(
        count=len(files),
        criteria=criteria.strip(),
    )
    content.append({"type": "text", "text": user_prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        response = requests.post(
            API_BASE_URL, headers=headers, json=payload, timeout=180
        )
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "API request timed out (180s). Resumes may be too large or too many.",
        }
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"API request failed: {e}"}

    if response.status_code == 401 or response.status_code == 403:
        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", str(error_data))
        except Exception:
            error_msg = response.text
        return {
            "success": False,
            "error": (
                f"API authentication failed: {error_msg}. "
                "Please check your ZHIPU_API_KEY at: https://bigmodel.cn/usercenter/proj-mgmt/apikeys. "
                "认证失败，请检查或更新你的 ZHIPU_API_KEY。"
            ),
            "status_code": response.status_code,
        }

    if response.status_code != 200:
        try:
            error_data = response.json()
        except Exception:
            error_data = response.text
        return {
            "success": False,
            "error": f"API request failed: {response.status_code} - {error_data}",
            "status_code": response.status_code,
        }

    result = response.json()

    caption = ""
    finish_reason = ""
    if result.get("choices"):
        caption = result["choices"][0].get("message", {}).get("content", "")
        finish_reason = result["choices"][0].get("finish_reason", "")

    out = {
        "success": True,
        "result": caption,
        "usage": result.get("usage", {}),
        "criteria": criteria,
        "file_count": len(files),
    }
    if finish_reason == "sensitive":
        out["warning"] = "Content blocked by safety review (finish_reason: sensitive)"
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Screen resumes using GLM-V model — read resumes and evaluate against criteria"
    )

    parser.add_argument(
        "--files",
        "-f",
        nargs="+",
        required=True,
        help="Resume file URLs (pdf/docx/txt, URL only, max 50)",
    )
    parser.add_argument(
        "--criteria",
        "-c",
        required=True,
        help="Screening criteria (e.g., '3+ years experience, Python skills')",
    )
    parser.add_argument(
        "--model", "-m", default=DEFAULT_MODEL, help="Model name (default: glm-4.6v)"
    )
    parser.add_argument(
        "--system-prompt",
        "-s",
        default=None,
        help="Custom system prompt (default: professional HR assistant)",
    )
    parser.add_argument(
        "--temperature",
        "-t",
        type=float,
        default=0.3,
        help="Sampling temperature 0-1 (default: 0.3 for consistent evaluation)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Max output tokens (default: model's default)",
    )
    parser.add_argument(
        "--output", "-o", default=None, help="Save result to file (.md or .json)"
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )

    args = parser.parse_args()

    # Resolve default max_tokens from MODEL_MAX_TOKENS table
    resolved_max_tokens = args.max_tokens
    if resolved_max_tokens is None:
        model_key = args.model.lower()
        model_limits = MODEL_MAX_TOKENS.get(model_key)
        resolved_max_tokens = model_limits["default"] if model_limits else 4096

    try:
        result = screen(
            files=args.files,
            criteria=args.criteria,
            model=args.model,
            system_prompt=args.system_prompt,
            temperature=args.temperature,
            max_tokens=resolved_max_tokens,
        )
    except Exception as e:
        result = {"success": False, "error": str(e)}

    if not result.get("success"):
        indent = 2 if args.pretty else None
        print(json.dumps(result, ensure_ascii=False, indent=indent))
        sys.exit(1)

    # Output
    if args.output and args.output.endswith(".md"):
        # Save as markdown (extract just the table/content)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write("# 简历筛选结果\n\n")
            f.write(f"**筛选标准：** {args.criteria}\n\n")
            f.write(f"**简历数量：** {result.get('file_count', 0)} 份\n\n")
            f.write("---\n\n")
            f.write(result.get("result", ""))
        print(f"Result saved to: {args.output}", file=sys.stderr)
    elif args.output:
        # Save as JSON
        indent = 2 if args.pretty else None
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=indent)
        print(f"Result saved to: {args.output}", file=sys.stderr)
    else:
        # Print markdown result to stdout
        print(result.get("result", ""))


if __name__ == "__main__":
    main()
