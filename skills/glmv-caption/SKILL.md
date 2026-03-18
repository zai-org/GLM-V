---
name: glmv-caption
description:
  Generate captions (descriptions) for images, videos, and documents using ZhiPu
  GLM-V multimodal model series. Use this skill whenever the user wants to describe,
  caption, summarize, or interpret the content of images, videos, or files.
  Supports single/multiple inputs, URLs, local paths, and base64 (images only).
metadata:
  openclaw:
    requires:
      env:
        - ZHIPU_API_KEY
      bins:
        - python
    primaryEnv: ZHIPU_API_KEY
    emoji: "🖼️"
    homepage: https://github.com/zai-org/GLM-V/tree/main/skills/glmv-caption
---

# GLM-V Caption Skill

Generate captions for images, videos, and documents using the ZhiPu GLM-V multimodal model.

## When to Use

- Describe, caption, summarize, or interpret image/video/document content
- User mentions "describe this image", "caption", "summarize this video", "图片描述", "视频摘要", "文档解读", "看图说话"
- Extract visual or textual information from media files
- Compare multiple images
- User provides an image/video/file and asks what's in it

## Supported Input Types

| Type  | Formats                           | Max Size          | Max Count | Base64 |
| ----- | --------------------------------- | ----------------- | --------- | ------ |
| Image | jpg, png, jpeg                    | 5MB / 6000×6000px | 50        | ✅     |
| Video | mp4, mkv, mov                     | 200MB             | —         | ❌     |
| File  | pdf, docx, txt, xlsx, pptx, jsonl | —                 | 50        | ❌     |

**⚠️ file_url cannot mix with image_url or video_url in the same request.**
**⚠️ Videos and files only support URLs — local paths and base64 are NOT supported (images only).**

## Resource Links

| Resource        | Link                                                                                                                              |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Get API Key** | [https://bigmodel.cn/usercenter/proj-mgmt/apikeys](https://bigmodel.cn/usercenter/proj-mgmt/apikeys)                              |
| **API Docs**    | [Chat Completions / 对话补全](https://docs.bigmodel.cn/api-reference/%E6%A8%A1%E5%9E%8B-api/%E5%AF%B9%E8%AF%9D%E8%A1%A5%E5%85%A8) |

## Prerequisites

### API Key Setup / API Key 配置（Required / 必需）

This script reads the key from the `ZHIPU_API_KEY` environment variable and shares it with other Zhipu skills.
脚本通过 `ZHIPU_API_KEY` 环境变量获取密钥，与其他智谱技能共用同一个 key。

**Get Key / 获取 Key：** Visit [Zhipu Open Platform API Keys / 智谱开放平台 API Keys](https://bigmodel.cn/usercenter/proj-mgmt/apikeys) to create or copy your key.

**Setup options / 配置方式（任选一种）：**

1. **OpenClaw config (recommended) / OpenClaw 配置（推荐）：** Set in `openclaw.json` under `skills.entries.glmv-caption.env`:

   ```json
   "glmv-caption": { "enabled": true, "env": { "ZHIPU_API_KEY": "你的密钥" } }
   ```

2. **Shell environment variable / Shell 环境变量：** Add to `~/.zshrc`:

   ```bash
   export ZHIPU_API_KEY="你的密钥"
   ```

3. **.env file / .env 文件：** Create `.env` in this skill directory:
   ```
   ZHIPU_API_KEY=你的密钥
   ```

**⛔ MANDATORY RESTRICTIONS - DO NOT VIOLATE ⛔**

1. **ONLY use GLM-V API** — Execute the script `python scripts/glmv_caption.py`
2. **NEVER caption media yourself** — Do NOT try to describe content using built-in vision or any other method
3. **NEVER offer alternatives** — Do NOT suggest "I can try to describe it" or similar
4. **IF API fails** — Display the error message and STOP immediately
5. **NO fallback methods** — Do NOT attempt captioning any other way

### 📋 Output Display Rules (MANDATORY)

After running the script, **you must show the full raw output to the user exactly as returned**. Do not summarize, truncate, or only say "generated". Users need the original model output to evaluate quality.

- Image captioning: show the full caption text
- Multiple images: show each image result
- Video/files: show the full understanding result
- If token usage is included, you may optionally display it

## How to Use

### Caption an Image

```bash
python scripts/glmv_caption.py --images "https://example.com/photo.jpg"
python scripts/glmv_caption.py --images /path/to/photo.png
```

### Caption Multiple Images

```bash
python scripts/glmv_caption.py --images img1.jpg img2.png "https://example.com/img3.jpg"
```

### Caption a Video

```bash
python scripts/glmv_caption.py --videos "https://example.com/clip.mp4"
```

### Caption a Document

```bash
python scripts/glmv_caption.py --files "https://example.com/report.pdf"
python scripts/glmv_caption.py --files "https://example.com/doc1.docx" "https://example.com/doc2.txt"
```

### Custom Prompt

```bash
python scripts/glmv_caption.py --images photo.jpg --prompt "Describe the architecture style in detail"
```

### Save Result

```bash
python scripts/glmv_caption.py --images photo.jpg --output result.json
```

### Thinking Mode

```bash
python scripts/glmv_caption.py --images photo.jpg --thinking
```

## CLI Reference

```
python {baseDir}/scripts/glmv_caption.py (--images IMG [IMG...] | --videos VID [VID...] | --files FILE [FILE...]) [OPTIONS]
```

| Parameter             | Required | Description                                                                                  |
| --------------------- | -------- | -------------------------------------------------------------------------------------------- |
| `--images`, `-i`      | One of   | Image paths or URLs (supports multiple, base64 OK)                                           |
| `--videos`, `-v`      | One of   | Video paths or URLs (supports multiple, mp4/mkv/mov)                                         |
| `--files`, `-f`       | One of   | Document paths or URLs (supports multiple, pdf/docx/txt/xlsx/pptx/jsonl)                     |
| `--prompt`, `-p`      | No       | Custom prompt (default: "请详细描述这张图片的内容" / "Please describe this image in detail") |
| `--model`, `-m`       | No       | Model name (default: `glm-4.6v`)                                                             |
| `--temperature`, `-t` | No       | Sampling temperature 0-1 (default: 0.8)                                                      |
| `--top-p`             | No       | Nucleus sampling 0.01-1.0 (default: 0.6)                                                     |
| `--max-tokens`        | No       | Max output tokens (default: 1024, max 32768)                                                 |
| `--thinking`          | No       | Enable thinking/reasoning mode                                                               |
| `--output`, `-o`      | No       | Save result JSON to file                                                                     |
| `--pretty`            | No       | Pretty-print JSON output                                                                     |
| `--stream`            | No       | Enable streaming output                                                                      |

**Note:** `--images`, `--videos`, and `--files` are mutually exclusive per API limits.

## Response Format

```json
{
  "success": true,
  "caption": "A landscape photo showing a mountain range at sunset...",
  "usage": {
    "prompt_tokens": 128,
    "completion_tokens": 256,
    "total_tokens": 384
  }
}
```

Key fields:

- `success` — whether the request succeeded
- `caption` — the generated caption text
- `usage` — token usage statistics
- `warning` — present when content was blocked by safety review
- `error` — error details on failure

## Error Handling

**API key not configured:**

```
ZHIPU_API_KEY not configured. Get your API key at: https://bigmodel.cn/usercenter/proj-mgmt/apikeys
```

→ Show exact error to user, guide them to configure

**Authentication failed (401/403):** API key invalid/expired → reconfigure

**Rate limit (429):** Quota exhausted → inform user to wait

**File not found:** Local file missing → check path

**Content filtered:** `warning` field present → content blocked by safety review
