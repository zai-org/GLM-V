"""
GLM-V Prompt Generation Tool
Use Zhipu GLM-V vision models to analyze images/videos and generate prompts for text-to-image and text-to-video workflows.

Official API docs (https://docs.bigmodel.cn/api-reference/模型-api/对话补全):
Vision model enum: glm-4.6v, autoglm-phone, glm-4.6v-flash, glm-4.6v-flashx, glm-4v-flash, glm-4.1v-thinking-flashx, glm-4.1v-thinking-flash

- Images: URL or Base64, ≤5MB each, ≤6000×6000px, only jpg/png/jpeg
- Videos: URL only (no local path, no base64), mp4/mkv/mov, ≤200MB
- GLM-4.6V/GLM-4.6V-Flash/GLM-4.6V-FlashX: ≤50 images
- GLM-4V-Flash: ≤1 image, NO Base64
- image_url and video_url cannot mix in the same request
"""

import os
import json
import base64
import argparse
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

import requests

DEFAULT_MODEL = "glm-5v-turbo"
API_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# Model max_tokens limits (per official docs)
MODEL_MAX_TOKENS = {
    "glm-4.6v": {"default": 16384, "max": 32768},
    "glm-4.6v-flash": {"default": 16384, "max": 32768},
    "glm-4.6v-flashx": {"default": 16384, "max": 32768},
}

# Max images per model
MODEL_IMAGE_LIMITS = {
    "glm-4.6v": 50,
    "glm-4.6v-flash": 50,
    "glm-4.6v-flashx": 50,
}

# Models that do NOT support Base64 (URL only)
NO_BASE64_MODELS = {"glm-4v-flash"}

SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
IMAGE_MIME_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
MAX_IMAGE_SIZE_MB = 5

OUTPUT_IMAGE = "image"
OUTPUT_VIDEO = "video"

OUTPUT_FORMAT_RULE = (
    "## 输出格式\n"
    "只输出两部分，不要任何多余内容：\n"
    "### 内容分析\n"
    "（用中文写一段完整的文字，详细描述素材的内容和视觉特征。\n"
    "不要分点、不要列表，写成一段连贯流畅的分析，\n"
    "涵盖主体、风格、色调、光影、构图、氛围、细节等所有你观察到的要素。）\n\n"
    "### Prompt\n"
    "（根据语言判断规则，用中文或英文生成一段可直接复制使用的 prompt。\n"
    "写成一段完整、流畅、描述性强的文字，不要用分点或列表。\n"
    "必须涵盖以下六个要素，各要素之间用自然的语言衔接，不要生硬罗列：\n"
    "1. 主体：画面核心对象及其状态、动作、表情等\n"
    "2. 风格：如写实摄影、油画、水彩、赛博朋克、扁平插画等\n"
    "3. 色调：整体色彩倾向、主色调、色彩对比关系\n"
    "4. 光影：光源方向、明暗对比、特殊光效（逆光、侧光、柔光等）\n"
    "5. 构图：视角（俯视/平视/仰视）、景别（特写/中景/远景）、画面布局\n"
    "6. 氛围：整体情绪和感受（温馨/冷峻/神秘/欢快等）\n"
    "不要遗漏任何要素，这段 prompt 就是用户最终复制粘贴到生图/生视频工具里的东西。）\n"
)

LANG_RULE = (
    "## 语言判断规则\n"
    "根据参考素材的内容自动判断 prompt 应使用中文还是英文，只输出一种语言：\n"
    "- 如果素材包含中文文字、中国元素（如中文品牌、中国场景、中国文化符号等），"
    "用**中文**生成 prompt\n"
    "- 如果素材为纯西式内容（英文文字、西方场景、国际品牌等），"
    "用**英文**生成 prompt\n"
    "- 纯图片无文字时，根据视觉风格判断：西式时尚/摄影/建筑等用英文，中式场景用中文\n"
    "- 判断模糊时，优先输出中文 prompt\n"
    "- 绝不要同时输出中英两个版本\n"
)

SYSTEM_PROMPT_IMAGE = (
    "你是一位专业的 AI 绘画 prompt 工程师。分析用户提供的参考图片，生成可直接用于文生图工具的 prompt。\n\n"
    "## 工作流程\n"
    "1. 仔细观察参考图片的：构图、风格、色调、光影、主体、氛围、细节\n"
    "2. 提炼关键视觉元素\n"
    "3. 根据素材内容判断语言，生成一段完整的 prompt\n\n"
    + LANG_RULE
    + "\n"
    + OUTPUT_FORMAT_RULE
)

SYSTEM_PROMPT_VIDEO = (
    "你是一位专业的 AI 视频生成 prompt 工程师。分析用户提供的参考视频，生成可直接用于文生视频工具的 prompt。\n\n"
    "## 工作流程\n"
    "1. 仔细观察参考视频的：场景、动作、镜头运动、节奏、风格、色调、主体、氛围\n"
    "2. 提炼关键视觉和动态元素\n"
    "3. 根据素材内容判断语言，生成一段完整的 prompt\n\n"
    + LANG_RULE
    + "\n"
    + OUTPUT_FORMAT_RULE
)

SYSTEM_PROMPT_AUTO = (
    "你是一位专业的 AI 创意 prompt 工程师。分析用户提供的参考素材，生成可直接用于文生图和文生视频工具的 prompt。\n\n"
    "## 工作流程\n"
    "1. 仔细观察参考素材的内容、风格、色调、光影、构图/镜头、主体、氛围\n"
    "2. 提炼关键视觉元素\n"
    "3. 根据素材内容判断语言，分别生成文生图和文生视频两段 prompt\n\n"
    + LANG_RULE
    + "\n"
    "## 输出格式\n"
    "只输出三部分，不要任何多余内容：\n"
    "### 内容分析\n"
    "（用中文写一段完整的文字，详细描述素材的内容和视觉特征，不要分点列表。）\n\n"
    "### 文生图 Prompt\n"
    "（根据语言判断规则，用中文或英文生成一段完整描述性段落，可直接复制使用。\n"
    "必须涵盖主体、风格、色调、光影、构图、氛围六个要素，用自然语言衔接。）\n\n"
    "### 文生视频 Prompt\n"
    "（根据语言判断规则，用中文或英文生成一段完整描述性段落，可直接复制使用。\n"
    "必须涵盖场景、主体动作、镜头运动、风格、色调光影、节奏氛围六个要素，用自然语言衔接。）\n"
)


def _is_url(s: str) -> bool:
    return s.strip().startswith(("http://", "https://"))


def load_image_as_data_url(image_path: str) -> str:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    ext = path.suffix.lower()
    if ext not in SUPPORTED_IMAGE_EXTS:
        raise ValueError(
            f"Unsupported image format '{ext}'. Only {', '.join(sorted(SUPPORTED_IMAGE_EXTS))} are supported."
        )
    size_bytes = path.stat().st_size
    max_bytes = MAX_IMAGE_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise ValueError(
            f"Image too large: {size_bytes / 1024 / 1024:.1f}MB (max {MAX_IMAGE_SIZE_MB}MB)."
        )
    mime_type = IMAGE_MIME_TYPES[ext]
    with open(path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode()
    return f"data:{mime_type};base64,{img_data}"


def process_image(image_input: str) -> str:
    image_input = image_input.strip()
    if image_input.startswith("data:"):
        return image_input
    if image_input.startswith("base64:"):
        return f"data:image/jpeg;base64,{image_input[7:]}"
    if _is_url(image_input):
        return image_input
    return load_image_as_data_url(image_input)


def generate(
    images: Optional[List[str]] = None,
    videos: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    output_mode: str = OUTPUT_IMAGE,
    temperature: float = 0.6,
    max_tokens: int = 2048,
    thinking: bool = False,
    stream: bool = False,
) -> Dict[str, Any]:
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

    if not images and not videos:
        return {"success": False, "error": "No images or videos provided."}

    model_key = model.lower()
    model_limits = MODEL_MAX_TOKENS.get(model_key)
    if model_limits and max_tokens > model_limits["max"]:
        return {
            "success": False,
            "error": f"max_tokens {max_tokens} exceeds model '{model}' limit of {model_limits['max']}.",
        }

    if images:
        max_images = MODEL_IMAGE_LIMITS.get(model_key, 50)
        if len(images) > max_images:
            return {
                "success": False,
                "error": f"Too many images: {len(images)} (max {max_images} for model '{model}').",
            }
        if model_key in NO_BASE64_MODELS:
            for img in images:
                if not _is_url(img):
                    return {
                        "success": False,
                        "error": f"Model '{model}' does not support Base64 or local files. Use URLs only.",
                    }

    if videos:
        for v in videos:
            if not _is_url(v):
                return {
                    "success": False,
                    "error": f"Videos must be URLs, not local paths: {v}",
                }

    if output_mode == OUTPUT_IMAGE:
        system_prompt = SYSTEM_PROMPT_IMAGE
    elif output_mode == OUTPUT_VIDEO:
        system_prompt = SYSTEM_PROMPT_VIDEO
    else:
        system_prompt = SYSTEM_PROMPT_AUTO

    content = []
    if images:
        for img in images:
            content.append(
                {"type": "image_url", "image_url": {"url": process_image(img)}}
            )
    elif videos:
        for vid in videos:
            content.append({"type": "video_url", "video_url": {"url": vid.strip()}})

    content.append(
        {
            "type": "text",
            "text": "请分析以上参考素材，生成可以直接用于 AI 生图/生视频工具的 prompt。",
        }
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }

    if thinking:
        payload["thinking"] = {"type": "enabled"}

    try:
        response = requests.post(
            API_BASE_URL, headers=headers, json=payload, stream=stream, timeout=180
        )
    except requests.exceptions.Timeout:
        return {"success": False, "error": "API request timed out (180s)."}
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

    if stream:
        full_content = ""
        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8")
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    if "content" in delta:
                        full_content += delta["content"]
                        print(delta["content"], end="", flush=True)
                except Exception:
                    pass
        print()
        return {"success": True, "result": full_content}

    result = response.json()
    caption = ""
    finish_reason = ""
    if result.get("choices"):
        caption = result["choices"][0].get("message", {}).get("content", "")
        finish_reason = result["choices"][0].get("finish_reason", "")

    out = {
        "success": True,
        "result": caption,
        "output_mode": output_mode,
        "usage": result.get("usage", {}),
    }
    if finish_reason == "sensitive":
        out["warning"] = "Content blocked by safety review (finish_reason: sensitive)"
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Generate prompts for text-to-image/text-to-video from reference images or videos using GLM-V"
    )

    input_group = parser.add_argument_group("Input (pick one)")
    input_group.add_argument(
        "--images",
        "-i",
        nargs="+",
        help="Image paths or URLs (jpg/png/jpeg, base64 OK)",
    )
    input_group.add_argument(
        "--videos", "-v", nargs="+", help="Video URLs (mp4/mkv/mov, URL only)"
    )

    parser.add_argument(
        "--mode",
        "-m",
        default=OUTPUT_IMAGE,
        choices=[OUTPUT_IMAGE, OUTPUT_VIDEO, "auto"],
        help="Output prompt type: image (default), video, or auto (both)",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help="Model name (default: glm-4.6v)"
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
        "--thinking", action="store_true", help="Enable thinking/reasoning mode"
    )
    parser.add_argument("--stream", action="store_true", help="Enable streaming output")
    parser.add_argument("--output", "-o", help="Save result to file")
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON error output"
    )

    args = parser.parse_args()

    input_count = sum(1 for x in [args.images, args.videos] if x)
    if input_count == 0:
        parser.error("Must provide one of: --images, --videos")
    if input_count > 1:
        parser.error("--images and --videos are mutually exclusive")

    # Resolve default max_tokens from MODEL_MAX_TOKENS table
    resolved_max_tokens = args.max_tokens
    if resolved_max_tokens is None:
        model_key = args.model.lower()
        model_limits = MODEL_MAX_TOKENS.get(model_key)
        resolved_max_tokens = model_limits["default"] if model_limits else 4096

    try:
        result = generate(
            images=args.images,
            videos=args.videos,
            model=args.model,
            output_mode=args.mode,
            temperature=args.temperature,
            max_tokens=resolved_max_tokens,
            thinking=args.thinking,
            stream=args.stream,
        )
    except Exception as e:
        result = {"success": False, "error": str(e)}

    if args.stream:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\nResult saved to: {args.output}", file=sys.stderr)
        return

    if not result.get("success"):
        indent = 2 if args.pretty else None
        print(json.dumps(result, ensure_ascii=False, indent=indent))
        sys.exit(1)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result.get("result", ""))
        print(f"Result saved to: {args.output}", file=sys.stderr)
    else:
        print(result.get("result", ""))


if __name__ == "__main__":
    main()
