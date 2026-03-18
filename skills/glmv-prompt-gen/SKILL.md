---
name: glmv-prompt-gen
description:
  Analyze images/videos and generate professional prompts for text-to-image and
  text-to-video AI tools (Midjourney, Stable Diffusion, DALL-E, Sora, Runway, Kling, Pika).
  Use when the user wants to generate prompts from reference images/videos, create
  AI art prompts, or get prompt engineering suggestions from visual content.
metadata:
   openclaw:
      requires:
         env:
            - ZHIPU_API_KEY
         bins:
            - python
      primaryEnv: ZHIPU_API_KEY
      emoji: "✨"
      homepage: https://github.com/zai-org/GLM-V/tree/main/skills/glmv-prompt-gen
---

# GLM-V Prompt Generation Skill

Analyze reference images or videos and generate professional prompts for AI image/video generation tools.

## When to Use

- Generate prompts for text-to-image tools (Midjourney, Stable Diffusion, DALL-E, etc.)
- Generate prompts for text-to-video tools (Sora, Runway, Kling, Pika, etc.)
- User mentions "生成prompt", "文生图prompt", "文生视频prompt", "prompt工程", "参考图生成prompt", "generate prompt"
- User provides an image/video and wants to recreate or remix it
- Extract prompt ideas from reference visual content

## Supported Input Types

| Type  | Formats        | Max Size          | Max Count | Base64        |
| ----- | -------------- | ----------------- | --------- | ------------- |
| Image | jpg, png, jpeg | 5MB / 6000×6000px | 50        | ✅            |
| Video | mp4, mkv, mov  | 200MB             | —         | ❌ (URL only) |

> ⚠️ Images and videos cannot be used in the same request.
> ⚠️ Videos only support URLs — local paths and base64 are NOT supported.

### 📋 Output Display Rules (MANDATORY)

After running the script, **you must display the full prompt output exactly as returned**. Do not summarize, truncate, or only say "prompt generated". Users need the complete prompt (especially the English prompt) for direct copy/paste.

- Show the full output: content analysis + prompt + prompt breakdown
- In `auto` mode, show both text-to-image and text-to-video prompts
- English prompts are core output and must be shown completely
- If output was saved (`-o`), provide the file path and show file content

## Output Modes

| Mode    | Description                                        |
| ------- | -------------------------------------------------- |
| `image` | Generate prompts for text-to-image tools (default) |
| `video` | Generate prompts for text-to-video tools           |
| `auto`  | Generate prompts for both image and video          |

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

1. **OpenClaw config (recommended) / OpenClaw 配置（推荐）：** Set in `openclaw.json` under `skills.entries.glmv-prompt-gen.env`:

   ```json
   "glmv-prompt-gen": { "enabled": true, "env": { "ZHIPU_API_KEY": "你的密钥" } }
   ```

2. **Shell environment variable / Shell 环境变量：** Add to `~/.zshrc`:
   ```bash
   export ZHIPU_API_KEY="你的密钥"
   ```

> 💡 If you already configured another Zhipu skill (for example `zhipu-tools` or `glmv-caption`), they share the same `ZHIPU_API_KEY`, so no extra setup is needed.
> 💡 如果你已为其他智谱 skill（如 `zhipu-tools`、`glmv-caption`）配置过 key，它们共享同一个 `ZHIPU_API_KEY`，无需重复配置。

## How to Use

### Image → Text-to-Image Prompt

```bash
python scripts/prompt_gen.py --images "https://example.com/photo.jpg"
python scripts/prompt_gen.py --images /path/to/photo.png
```

### Image → Text-to-Video Prompt

```bash
python scripts/prompt_gen.py --images "https://example.com/scene.jpg" --mode video
```

### Image → Both (Image + Video Prompts)

```bash
python scripts/prompt_gen.py --images "https://example.com/photo.jpg" --mode auto
```

### Video → Text-to-Video Prompt

```bash
python scripts/prompt_gen.py --videos "https://example.com/clip.mp4" --mode video
```

### Save Result to File

```bash
python scripts/prompt_gen.py --images photo.jpg --mode image -o prompt.md
```

### Custom Model

```bash
python scripts/prompt_gen.py --images photo.jpg --model glm-4.6v-flash
```

## Output Example (image mode)

```
### Content Analysis
A cyberpunk cityscape at night, with dense skyscrapers, glowing neon signs, and rain-wet streets reflecting colorful light.

### Prompt
Cyberpunk cityscape at night, towering skyscrapers with glowing neon signs,
rain-wet streets reflecting colorful lights, flying cars in the distance,
volumetric fog, dramatic lighting, ultra detailed, 8K, cinematic composition

### Prompt Breakdown
- **Subject**: Futuristic skyline with skyscrapers and neon lights
- **Style**: Cyberpunk, sci-fi
- **Color**: Cool/warm contrast with blue-purple dominance and neon accents
- **Lighting**: Neon glow, wet-surface reflections, volumetric fog
- **Composition**: Wide-angle perspective with layered depth
- **Mood**: Mysterious, futuristic, high-tech
```

## CLI Reference

```
python scripts/prompt_gen.py (--images IMG [IMG...] | --videos VID [VID...]) [OPTIONS]
```

| Parameter             | Required | Description                                        |
| --------------------- | -------- | -------------------------------------------------- |
| `--images`, `-i`      | One of   | Image paths or URLs (jpg/png/jpeg, base64 OK)      |
| `--videos`, `-v`      | One of   | Video URLs (mp4/mkv/mov, URL only)                 |
| `--mode`, `-m`        | No       | Output mode: `image` (default), `video`, or `auto` |
| `--model`             | No       | Model name (default: `glm-4.6v`)                   |
| `--temperature`, `-t` | No       | Sampling temperature 0-1 (default: 0.6)            |
| `--max-tokens`        | No       | Max output tokens (default: 2048)                  |
| `--thinking`          | No       | Enable thinking/reasoning mode                     |
| `--stream`            | No       | Enable streaming output                            |
| `--output`, `-o`      | No       | Save result to file                                |
| `--pretty`            | No       | Pretty-print JSON error output                     |

## Error Handling

**API key not configured:** → Guide user to configure `ZHIPU_API_KEY`

**Authentication failed (401/403):** → API key invalid/expired → check at [Zhipu API Keys / 智谱官网](https://bigmodel.cn/usercenter/proj-mgmt/apikeys)

**Rate limit (429):** → Quota exhausted → wait and retry

**Content filtered:** → `warning` field present → content blocked by safety review

**Timeout:** → Video processing may take time → increase timeout or use smaller files
