#!/usr/bin/env python3
"""
GLM-Grounding CLI

Command-line interface for GLM-V vision model.

Usage:
    python scripts/glm_grounding_cli.py --file-url "URL" --prompt "description of target for grounding"
    python scripts/glm_grounding_cli.py --file-url "URL" --prompt "description of target for grounding" --visualize --visualization-dir "./vis"
"""

import argparse
import base64
import io
import json
import logging
import mimetypes
import os
import socket
import sys
import ipaddress
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from utils_boxes import (
    parse_coordinates_from_response,
    visualize_boxes,
)
from utils_detection import parse_detection_from_response
from utils_video import parse_mot_from_response, visualize_mot

try:
    import requests
except ImportError:
    print(
        "Error: Missing dependency 'requests'. Install with: pip install -r scripts/requirements.txt",
        file=sys.stderr,
    )
    sys.exit(2)

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

DEFAULT_TIMEOUT = 60  # seconds
DEFAULT_MODEL = "glm-5v-turbo"
API_GUIDE_URL = "https://open.bigmodel.cn/usercenter/apikeys"
DEFAULT_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# =============================================================================
# Environment
# =============================================================================

_env_loaded = False


def _load_env():
    """Load .env file if available."""
    global _env_loaded
    if _env_loaded:
        return

    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if key and key not in os.environ:
                        os.environ[key] = value
        except OSError as e:
            logger.debug(f"Failed to load .env: {e}")

    _env_loaded = True


def _get_env(key: str, *fallback_keys: str) -> str:
    """Get environment variable with fallback keys."""
    _load_env()
    value = os.getenv(key, "").strip()
    if value:
        return value
    for fallback in fallback_keys:
        value = os.getenv(fallback, "").strip()
        if value:
            logger.debug(f"Using fallback env var: {fallback}")
            return value
    return ""


def get_config() -> tuple[str, str]:
    """
    Get API URL and key from environment.

    Returns:
        tuple of (api_url, api_key)

    Raises:
        ValueError: If not configured
    """
    api_key = _get_env("ZHIPU_API_KEY")

    if not api_key:
        raise ValueError(
            f"ZHIPU_API_KEY not configured. Get your API key at: {API_GUIDE_URL}"
        )

    # Security: use fixed official endpoint to avoid key exfiltration via custom URL.
    return DEFAULT_API_URL, api_key


# =============================================================================
# File Utilities
# =============================================================================


def _is_url(path: str) -> bool:
    """Check if the given path is a URL."""
    try:
        result = urlparse(path)
        return all([result.scheme, result.netloc]) and result.scheme in (
            "http",
            "https",
        )
    except Exception:
        return False


def _is_public_url(url: str) -> tuple[bool, str]:
    """Validate URL is http/https and not localhost/private network target."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False, "Only http/https URLs are supported"

        host = parsed.hostname
        if not host:
            return False, "Invalid URL host"

        host_l = host.lower()
        if host_l in {"localhost", "127.0.0.1", "::1"}:
            return False, "Localhost URLs are not allowed"

        # Resolve and block private/link-local/loopback/reserved addresses.
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


def _encode_file(file_path: str) -> tuple[str, str]:
    """
    Encode a local file to base64 data URI.

    Returns:
        tuple of (data_uri, error_message)
        On success, error_message is empty.
    """
    path = Path(file_path)
    if not path.exists():
        return "", f"File not found: {file_path}"
    if not path.is_file():
        return "", f"Not a regular file: {file_path}"

    # Guess MIME type, fallback to application/octet-stream
    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        mime = "application/octet-stream"

    try:
        data = path.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{b64}", ""
    except Exception as e:
        return "", f"Failed to read file: {e}"


def load_media_bytes(source: str):
    """Get bytes for a media URL or local file path."""
    if _is_url(source):
        ok, reason = _is_public_url(source)
        if not ok:
            return None, f"Rejected URL for security reasons: {reason}"
        try:
            resp = requests.get(source, timeout=10)
            resp.raise_for_status()
            return resp.content, ""
        except Exception as e:
            return None, f"Failed to download image: {e}"
    else:
        try:
            with open(source, "rb") as f:
                return f.read(), ""
        except OSError as e:
            return None, f"Failed to read file: {e}"


# =============================================================================
# API Request
# =============================================================================


def _make_api_request(api_url: str, api_key: str, payload: dict) -> dict:
    """
    Make GLM-Grounding API request.

    Args:
        api_url: API endpoint URL
        api_key: API key
        payload: Request payload

    Returns:
        API response dict

    Raises:
        RuntimeError: On API errors
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    timeout = float(os.getenv("GLM_GROUNDING_TIMEOUT", str(DEFAULT_TIMEOUT)))

    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
    except requests.Timeout:
        raise RuntimeError(f"API request timed out after {timeout}s")
    except requests.RequestException as e:
        raise RuntimeError(f"API request failed: {e}")

    # Handle HTTP errors
    if resp.status_code != 200:
        error_detail = ""
        try:
            error_body = resp.json()
            if isinstance(error_body, dict):
                error_detail = str(
                    error_body.get("error", {}).get("message", "")
                ).strip()
        except Exception:
            pass

        if not error_detail:
            error_detail = (resp.text[:200] or "No response body").strip()

        if resp.status_code == 401 or resp.status_code == 403:
            raise RuntimeError(
                f"Authentication failed ({resp.status_code}): {error_detail}"
            )
        elif resp.status_code == 429:
            raise RuntimeError(f"API rate limit exceeded (429): {error_detail}")
        elif resp.status_code >= 500:
            raise RuntimeError(
                f"API service error ({resp.status_code}): {error_detail}"
            )
        else:
            raise RuntimeError(f"API error ({resp.status_code}): {error_detail}")

    # Parse response
    try:
        result = resp.json()
    except Exception:
        raise RuntimeError(f"Invalid JSON response: {resp.text[:200]}")

    # Check API-level error
    if "error" in result:
        raise RuntimeError(f"API error: {result['error']}")

    return result


# =============================================================================
# Main API
# =============================================================================


def get_grounding_results(
    image: str | None,
    prompt: str,
    model: str = DEFAULT_MODEL,
    video: str | None = None,
    visualize: bool = False,
    visualization_dir: str | None = None,
    **options,
) -> dict[str, Any]:
    """
    Get visual grounding results by prompting GLM-V with an image/video and target description.

    Args:
        image: a URL or local file path to an image.
        prompt: Target description for visual grounding.
        model: Model to use (glm-4.6v, etc.)
        video: A URL or local file path to a video file.
        visualize: Whether to visualize the results.
        visualization_dir: Directory to save visualizations.
        **options: Additional API options:
            - enable_thinking: True - Whether to enable GLM-V's thinking mode. Default True.

    Returns:
        {
            "ok": True,
            "grounding_result": "Generated grounded results in coordinates or JSON format.",
            "visualizations_result": {"original_image_url": "path/to/visualization.jpg", ...} if visualize else None,
            "raw_result": { raw API result },
            "error": None,
            "source": "original source",
        }
        or on error:
        {
            "ok": False,
            "grounding_result": "",
            "visualizations_result": None,
            "raw_result": None,
            "error": {"code": "...", "message": "..."},
            "source": "original source",
        }
    """
    # Get config
    try:
        api_url, api_key = get_config()
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e), image or video or "")

    if not prompt or not prompt.strip():
        return _error("INPUT_ERROR", "Prompt cannot be empty", image or video or "")

    if bool(image) == bool(video):
        return _error(
            "INPUT_ERROR", "Provide exactly one of image or video", image or video or ""
        )

    source = image or video or ""

    content = [{"type": "text", "text": prompt}]

    mm_content = []
    if image:
        if not _is_url(image):
            encoded_image, encode_err = _encode_file(image)
            if encode_err:
                return _error("INPUT_ERROR", encode_err, source)
            image_for_api = encoded_image
        else:
            image_for_api = image
        mm_content.append({"type": "image_url", "image_url": {"url": image_for_api}})
    elif video is not None:  # video
        if not _is_url(video):
            encoded_video, encode_err = _encode_file(video)
            if encode_err:
                return _error("INPUT_ERROR", encode_err, source)
            video_for_api = encoded_video
        else:
            video_for_api = video
        mm_content.append({"type": "video_url", "video_url": {"url": video_for_api}})

    content = [*mm_content, *content]
    messages = [{"role": "user", "content": content}]

    # Build request payload
    payload = {
        "model": model,
        "messages": messages,
    }

    if options.get("enable_thinking", False):
        payload["thinking"] = {"type": "disabled"}

    # Call API
    try:
        raw_result = _make_api_request(api_url, api_key, payload)
    except RuntimeError as e:
        return _error("API_ERROR", str(e), source)

    # Parsers in utils expect text; normalize response to string once.
    raw_text = json.dumps(raw_result, ensure_ascii=False)

    # Parse grounding result
    if video:
        grounding_result = parse_mot_from_response(raw_text)
        boxes = []
        labels = []
    elif "bbox_2d" in raw_text or "bbox_3d" in raw_text:
        grounding_result = parse_detection_from_response(raw_text)
        boxes = [item["bbox_2d"] for item in grounding_result]
        labels = [item.get("label", "") for item in grounding_result]
    else:
        grounding_result = parse_coordinates_from_response(raw_text)
        boxes = grounding_result
        labels = [str(_) for _ in grounding_result]

    # Visualzie
    if visualize:
        visualization_dir = visualization_dir or "./visualization"
        os.makedirs(visualization_dir, exist_ok=True)
        media_bytes, media_err = load_media_bytes(source)
        if media_err:
            return _error("VISUALIZE_ERROR", media_err, source)

        if image:
            visualized_img_path = os.path.join(
                visualization_dir, f"{Path(source).stem}_grounding_visualized.jpg"
            )
            visualize_boxes(
                img_bytes=media_bytes,
                boxes=boxes,
                labels=labels,
                renormalize=True,
                save_path=visualized_img_path,
            )
        else:
            visualized_video_path = os.path.join(
                visualization_dir, f"{Path(source).stem}_grounding_visualized.mp4"
            )
            visualize_mot(
                video_bytes=media_bytes,
                mot_js=grounding_result,
                save_path=visualized_video_path,
            )

    return {
        "ok": True,
        "grounding": grounding_result,
        "visualizations_result": (
            {"visualized_image": visualized_img_path}
            if visualize and image
            else (
                {"visualized_video": visualized_video_path}
                if visualize and video
                else None
            )
        ),
        "raw_result": raw_result,
        "error": None,
        "source": source,
    }


def _error(code: str, message: str, source: str = "") -> dict:
    """Create error response."""
    return {
        "ok": False,
        "text": "",
        "layout_details": None,
        "result": None,
        "error": {"code": code, "message": message},
        "source": source,
        "source_type": "url" if _is_url(source) else "file",
    }


# =============================================================================
# CLI Interface
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="GLM-Grounding - Grounding anything in images/videos with GLM-V",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run for remote URL
  python scripts/glm_grounding_cli.py --image-url "https://example.com/image.jpg" --prompt "description of target for grounding"


  # Run for local video with visualization
  python scripts/glm_grounding_cli.py --video-url "https://example.com/video.mp4" --prompt "description of target for trackinging" --visualize --visualization-dir "./vis"

Configuration:
  Run: python scripts/config_setup.py setup
    Or set in .env: ZHIPU_API_KEY
        """,
    )

    parser.add_argument("--image-url", help="URL or local path to image/PDF")
    parser.add_argument("--prompt", "-p", required=True, help="Prompt for grounding")
    parser.add_argument("--video-url", help="URL or local path to video")
    parser.add_argument(
        "--visualize", action="store_true", help="Visualize grounding results"
    )
    parser.add_argument("--visualization-dir", help="Directory to save visualizations")

    args = parser.parse_args()

    if bool(args.image_url) == bool(args.video_url):
        parser.error("Provide exactly one of --image-url or --video-url")

    result = get_grounding_results(
        image=args.image_url,
        prompt=args.prompt,
        video=args.video_url,
        visualize=args.visualize,
        visualization_dir=args.visualization_dir,
    )

    print(result)
    # Exit code based on result
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
