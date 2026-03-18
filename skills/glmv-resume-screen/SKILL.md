---
name: glmv-resume-screen
description:
  Screen and evaluate resumes against criteria using ZhiPu GLM-V multimodal model.
  Reads multiple resume files (PDF/DOCX/TXT), compares against user-defined screening
  criteria, and outputs a Markdown table with pass/fail analysis. Use when the user
  wants to filter resumes, compare candidates, or batch-evaluate job applications.
metadata:
  openclaw:
    requires:
      env:
        - ZHIPU_API_KEY
      bins:
        - python
    primaryEnv: ZHIPU_API_KEY
    emoji: "🧾"
    homepage: https://github.com/zai-org/GLM-V/tree/main/skills/glmv-resume-screen
---

# GLM-V Resume Screening Skill

Batch-read resumes and screen candidates against your criteria using the ZhiPu GLM-V multimodal model.

## When to Use

- Filter/screen multiple resumes against specific criteria
- User mentions "筛选简历", "评估候选人", "简历筛选", "resume screening", "filter candidates"
- Compare candidates for a job position
- Batch-evaluate job applications

## Supported Input Types

| Type           | Formats        | Max Count        | Source     |
| -------------- | -------------- | ---------------- | ---------- |
| Resume (URL)   | pdf, docx, txt | 50               | URL        |
| Resume (Local) | pdf only       | pages ≤ 50 total | Local path |

> **Local PDF / 本地 PDF:** Local PDF files are converted page-by-page into images (base64) before sending to the model. `PyMuPDF` is required (`pip install PyMuPDF`). URL files support full formats including pdf/docx/txt.
> 本地 PDF 会自动逐页转为图片（base64）传给模型，需要安装 `PyMuPDF`（`pip install PyMuPDF`）。URL 文件支持 pdf/docx/txt 等全格式。

### 📋 Output Display Rules (MANDATORY)

After running the script, **you must display the complete screening result (Markdown table) exactly as returned**. Do not summarize, truncate, or only say "screening completed". Users need each candidate's detailed analysis to decide.

- Show the full Markdown table (index, name, pass/fail, match level, reasoning)
- If output was saved (`-o`), provide the file path and show file content
- If screening output is empty, explain why

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

1. **OpenClaw config (recommended) / OpenClaw 配置（推荐）：** Set in `openclaw.json` under `skills.entries.glmv-resume-screen.env`:

   ```json
   "glmv-resume-screen": { "enabled": true, "env": { "ZHIPU_API_KEY": "你的密钥" } }
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
python scripts/resume_screen.py \
  --files "https://example.com/resume1.pdf" "https://example.com/resume2.docx" \
  --criteria "3年以上工作经验，有Python开发经验，有大型项目管理经验"
```

### Save as Markdown

```bash
python scripts/resume_screen.py \
  --files "https://example.com/resume1.pdf" "https://example.com/resume2.docx" \
  --criteria "本科以上学历，5年后端开发经验" \
  --output result.md
```

### Save as JSON

```bash
python scripts/resume_screen.py \
  --files "https://example.com/resume1.pdf" "https://example.com/resume2.docx" \
  --criteria "有机器学习经验" \
  --output result.json --pretty
```

### Custom System Prompt

```bash
python scripts/resume_screen.py \
  --files "https://example.com/resume1.pdf" \
  --criteria "前端开发岗位，3年经验" \
  --system-prompt "你是一位资深技术面试官，特别关注候选人的项目深度和技术选型能力"
```

## Output Example

The model outputs a Markdown table like this:

```markdown
| 序号 | 候选人姓名 | 是否符合    | 符合程度 | 原因分析                                                    |
| ---- | ---------- | ----------- | -------- | ----------------------------------------------------------- |
| 1    | 张三       | ✅ 符合     | 高       | 5年后端经验，熟练使用Python和Django，主导过3个大型项目      |
| 2    | 李四       | ❌ 不符合   | 低       | 仅1年开发经验，主要使用Java，无Python经验                   |
| 3    | 王五       | ⚠️ 部分符合 | 中       | 3年Python经验但无项目管理经验，技术栈匹配但缺乏大型项目经历 |
```

## CLI Reference

```
python scripts/resume_screen.py --files FILE [FILE...] --criteria CRITERIA [OPTIONS]
```

| Parameter               | Required | Description                                                |
| ----------------------- | -------- | ---------------------------------------------------------- |
| `--files`, `-f`         | ✅       | Resume file URLs (pdf/docx/txt, URL only, max 50)          |
| `--criteria`, `-c`      | ✅       | Screening criteria text                                    |
| `--model`, `-m`         | No       | Model name (default: `glm-4.6v`)                           |
| `--system-prompt`, `-s` | No       | Custom system prompt (default: professional HR assistant)  |
| `--temperature`, `-t`   | No       | Sampling temperature 0-1 (default: 0.3)                    |
| `--max-tokens`          | No       | Max output tokens (default: 4096)                          |
| `--output`, `-o`        | No       | Save result to file (`.md` for markdown, `.json` for JSON) |
| `--pretty`              | No       | Pretty-print JSON output                                   |

## Error Handling

**API key not configured:** → Guide user to configure `ZHIPU_API_KEY`

**Authentication failed (401/403):** → API key invalid/expired → reconfigure

**Rate limit (429):** → Quota exhausted → wait and retry

**Local path provided:** → Error: only URLs supported

**Content filtered:** → `warning` field present → content blocked by safety review

**Timeout:** → Resumes too large or too many → reduce file count
