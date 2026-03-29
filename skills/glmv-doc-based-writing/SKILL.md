---
name: glmv-doc-based-writing
description:
  Write a textual content based on given document(s) and requirements, using ZhiPu GLM-V multimodal model.
  Read and comprehend one or multiple documents (PDF/DOCX), write a content in Markdown format according to the specified requirements. Use when the user wants to draft a paper/article/essay/report/review/post/brief/proposal/plan, etc.
metadata:
  openclaw:
    requires:
      env:
        - ZHIPU_API_KEY
      bins:
        - python
    primaryEnv: ZHIPU_API_KEY
    emoji: "✍️"
    homepage: https://github.com/zai-org/GLM-V/tree/main/skills/glmv-doc-based-writing
---

# GLM-V Document-Based Writing Skill

Comprehend the given document(s) and write a textual content (paper/article/essay/report/review/post/brief/proposal/plan) according to your requirements using the ZhiPu GLM-V multimodal model.

## When to Use

- Write a textual content according to specified requirements, AFTER reading provided document(s)
- User mentions "基于文档的写作", "文章撰写", "文档解读", "新闻稿撰写", "简报撰写", "影评/书评撰写", "内容总结", "内容创作", "评论写作", "文档续写", "文档翻译", "方案策划", "发言稿撰写", "document-based writing", "article writing", "document reading", "press release writing", "brief writing", "film/book review writing", "content summarization", "content creation", "commentary writing", "document continuation", "document translation", "proposal planning ", "speech writing"

## Supported Input Types

| Type             | Formats   | Max Count        | Source     |
| ---------------- | --------- | ---------------- | ---------- |
| Document (URL)   | pdf, docx | 50               | URL        |
| Document (Local) | pdf only  | pages ≤ 50 total | Local path |

> **Local PDF / 本地 PDF:** Local PDF files are converted page-by-page into images (base64) before sending to the model. `PyMuPDF` is required (`pip install PyMuPDF`). URL files support full formats including pdf/docx/txt.
> 本地 PDF 会自动逐页转为图片（base64）传给模型，需要安装 `PyMuPDF`（`pip install PyMuPDF`）。URL 文件支持 pdf/docx/txt 等全格式。

### 📋 Output Display Rules (MANDATORY)

After running the script, **you must display the complete content (Markdown format) exactly as returned**. Do not summarize, truncate, translate, comment, or only say "Writing Completed!".

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

1. **OpenClaw config (recommended) / OpenClaw 配置（推荐）：** Set in `openclaw.json` under `skills.entries.glmv-doc-based-writing.env`:

   ```json
   "glmv-doc-based-writing": { "enabled": true, "env": { "ZHIPU_API_KEY": "你的密钥" } }
   ```

2. **Shell environment variable / Shell 环境变量：** Add to `~/.zshrc`:
   ```bash
   export ZHIPU_API_KEY="你的密钥"
   ```

> 💡 If you already configured another Zhipu skill (for example `zhipu-tools` or `glmv-caption`), they share the same `ZHIPU_API_KEY`, so no extra setup is needed.
> 💡 如果你已为其他智谱 skill（如 `zhipu-tools`、`glmv-caption`）配置过 key，它们共享同一个 `ZHIPU_API_KEY`，无需重复配置。

## How to Use

### Basic Screening

```bash
python scripts/doc_based_writing.py \
  --files "https://example.com/doucment1.pdf" "https://example.com/doucment2.docx" \
  --requirements "基于这篇论文撰写公众号文章，要求偏技术风格"
```

### Save as Markdown

```bash
python scripts/doc_based_writing.py \
  --files "https://example.com/doucment1.pdf" "https://example.com/doucment2.docx" \
  --requirements "总结文档主要内容和核心观点" \
  --output result.md
```

### Save as JSON

```bash
python scripts/doc_based_writing.py \
  --files "https://example.com/doucment1.pdf" "https://example.com/doucment2.docx" \
  --criteria "撰写新闻稿" \
  --output result.json --pretty
```

### Custom System Prompt

```bash
python scripts/doc_based_writing.py \
  --files "https://example.com/doucment1.pdf" \
  --criteria "为这本书撰写书评" \
  --system-prompt "你是一位拥有20年跨领域写作经验的资深写作专家，擅长撰写书评"
```

## Output Example

The model outputs a Markdown content like this:

```markdown
XXX
```

## CLI Reference

```
python scripts/doc_based_writing.py --files FILE [FILE...] --requirements REQUIREMENTS [OPTIONS]
```

| Parameter               | Required | Description                                                |
| ----------------------- | -------- | ---------------------------------------------------------- |
| `--files`, `-f`          | ✅       | Document file URLs (pdf/docx, URL only, max 50)          |
| `--requirements`, `-c`  | ✅       | Writing requirements text                                    |
| `--model`, `-m`         | No       | Model name (default: `glm-4.6v`)                           |
| `--system-prompt`, `-s` | No       | Custom system prompt (default: professional HR assistant)  |
| `--temperature`, `-t`   | No       | Sampling temperature 0-1 (default: 0.6)                    |
| `--max-tokens`          | No       | Max output tokens (default: 10000)                          |
| `--output`, `-o`        | No       | Save result to file (`.md` for markdown, `.json` for JSON) |
| `--pretty`              | No       | Pretty-print JSON output                                   |

## Error Handling

**API key not configured:** → Guide user to configure `ZHIPU_API_KEY`

**Authentication failed (401/403):** → API key invalid/expired → reconfigure

**Rate limit (429):** → Quota exhausted → wait and retry

**Local path provided:** → Error: only URLs supported

**Content filtered:** → `warning` field present → content blocked by safety review

**Timeout:** → Documents too large or too many → reduce file count
