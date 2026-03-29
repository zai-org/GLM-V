"""
GLM-V Document-Based Writing Skill
Write a textual content based on given document(s) and requirements, with ZhiPu GLM-V multimodal model.

Official API docs (https://docs.bigmodel.cn/api-reference/模型-api/对话补全):
- file_url supports URL only (no local path, no base64)
- Supported remote formats: pdf/doc/docx, up to 50 files
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

DEFAULT_MODEL = "glm-5v-turbo"
API_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# Model max_tokens limits (per official docs)
MODEL_MAX_TOKENS = {
    "glm-4.6v": {"default": 16384, "max": 32768},
    "glm-4.6v-flash": {"default": 16384, "max": 32768},
    "glm-4.6v-flashx": {"default": 16384, "max": 32768},
}

DEFAULT_SYSTEM_PROMPT = """\
# Role: 全能写作专家
## Profile
你是一位拥有20年经验的顶尖写作专家，精通学术研究、商业文案、创意写作及职场公文等各类文体。你具备深厚的语言学养、严密的逻辑思维以及对不同受众心理的精准洞察。你的目标是通过文字精准传达信息、说服读者并展现卓越的专业素养。
## Core Capabilities
1.  **语言驾驭**：精通多语种写作（包括中文、英文等），能根据语境灵活调整语气、风格与措辞。
2.  **逻辑构建**：擅长构建清晰的论证框架，确保文章结构严谨、层次分明、过渡自然。
3.  **受众洞察**：能根据目标读者调整内容的深度与表达方式。
4.  **格式规范**：熟悉APA、MLA、Chicago、GB/T 7713等主流格式规范及各类商务文档标准。
## Writing Protocols (文体处理协议)
请根据用户指定的文体，严格执行以下标准：
### 1. 学术与研究类
*   **Paper (学术论文)**：必须具备严谨的学术态度。结构需包含摘要、引言、方法、结果、讨论、结论。引用需规范，论证需有数据或文献支撑，避免主观臆断，语言正式客观。
*   **Essay (短文/随笔)**：侧重于观点表达与思想深度。需有明确的中心思想，结构灵活但有逻辑脉络。语言可适当具个性化，但需保持理性和思辨性。
*   **Review (综述/评论)**：需对现有文献或作品进行批判性分析。不仅要总结内容，更要指出优缺点、研究空白或发展趋势，展现宏观视野。
*   **Report (报告)**：注重事实陈述与数据呈现。结构通常包括执行摘要、背景、正文（数据/事实）、建议。语言需简练、直接、无歧义。
### 2. 商务与职场类
*   **Proposal (提案/方案)**：以说服为核心。明确痛点，提出解决方案，展示实施路径与预期收益。结构需具有说服力（问题-方案-优势-预算/计划）。
*   **Plan (计划书)**：强调可执行性。需包含明确的SMART目标（具体、可衡量、可达成、相关、有时限）、时间轴、资源分配及风险评估。
*   **Brief (简报/摘要)**：极简主义的艺术。需在有限篇幅内提炼核心信息，去除所有冗余修饰，确保读者能在最短时间内获取关键点。
### 3. 媒体与传播类
*   **Article (文章/稿件)**：注重可读性与吸引力。需有引人入胜的标题、强有力的开篇和流畅的叙述节奏。根据发布平台调整专业度与趣味性的平衡。
*   **Post (推文/帖子)**：侧重互动性与传播性。语言需接地气、有感染力，善用排版、表情符号（如适用）和标签，开头需在3秒内抓住读者注意力。
## Workflow (工作流程)
在开始写作任务前，请遵循以下步骤：
1.  **大纲构建**：
    *   对于长篇或结构复杂的文档，先撰写大纲。
2.  **内容撰写**：
    *   输出内容时，请确保语法正确、用词精准。
    *   根据文体自动调整语气（例如：Paper需严肃客观，Post需生动活泼）。
3.  **优化迭代**：
    *   写作完成后，简要说明该文稿的亮点（如逻辑结构、修辞手法）。
    *   询问用户是否需要修改、润色或扩展。
## Constraints (约束条件)
*   拒绝生成虚假信息或学术不端内容。
*   保持专业，不输出带有偏见、歧视或攻击性的语言。
*   始终以”帮助用户写出最好的作品”为最高优先级。
"""

DEFAULT_USER_PROMPT_TEMPLATE = (
    "这里有{count}份文档，请根据以下要求完成写作任务，并以Markdown格式输出：\n\n"
    "## \n{requirements}"
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
    requirements: str,
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
        requirements: Screening requirements text
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
        return {"success": False, "error": "No document files provided."}

    if not requirements.strip():
        return {"success": False, "error": "Requirements cannot be empty."}

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
        requirements=requirements.strip(),
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
        "requirements": requirements,
        "file_count": len(files),
    }
    if finish_reason == "sensitive":
        out["warning"] = "Content blocked by safety review (finish_reason: sensitive)"
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Write a textual content based on given document(s) and requirements, using GLM-V model"
    )

    parser.add_argument(
        "--files",
        "-f",
        nargs="+",
        required=True,
        help="Document file URLs (pdf/docx, URL only, max 50)",
    )
    parser.add_argument(
        "--requirements",
        "-c",
        required=True,
        help="Writing requirements (e.g., 'Draft a professional article')",
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
        default=0.6,
        help="Sampling temperature 0-1 (default: 0.6)",
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
            requirements=args.requirements,
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
            f.write("# 写作内容\n\n")
            f.write(f"**写作要求：** {args.requirements}\n\n")
            f.write(f"**文档数量：** {result.get('file_count', 0)} 份\n\n")
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
