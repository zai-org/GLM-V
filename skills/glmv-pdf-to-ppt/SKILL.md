---
name: glmv-pdf-to-ppt
description:
  Convert a PDF (research paper, report, or any document) into a polished multi-slide
  HTML presentation with a structured outline JSON and summary markdown. Trigger this
  skill when the user mentions making slides or a PPT from a PDF — in Chinese or English.
metadata:
  openclaw:
    requires:
      bins:
        - python
    emoji: "📑"
    homepage: https://github.com/zai-org/GLM-V/tree/main/skills/glmv-pdf-to-ppt
---

# PDF → HTML PPT Skill

Convert any PDF into a multi-slide HTML presentation. Pages are converted to images at DPI 120, read sequentially to understand the content, then a structured `outline.json` is saved, images are cropped locally (no cloud upload), slides are rendered one by one, and finally a `summary.md` is generated.

**Scripts are in:** `{SKILL_DIR}/scripts/`

## Dependencies

Python packages (install once):
```bash
pip install pymupdf pillow
```

System tools: `curl` (pre-installed on macOS/Linux).

## When to Use

Trigger when the user asks to make slides or a presentation from a PDF — phrases like:
"make a PPT from a PDF", "convert PDF to slides", "create a presentation from this paper", "根据pdf做ppt", "根据论文做幻灯片", "做PPT", "做幻灯片", "生成演示文稿", "把这个pdf转成ppt", or any similar intent in Chinese or English.

## Output Directory Convention

All output goes under `{WORKSPACE}/ppt/<pdf_stem>_<timestamp>/`:

```
ppt/
└── <pdf_stem>_<timestamp>/
    ├── outline.json        ← structured slide plan (SlidesPlan schema)
    ├── crops/              ← locally-saved cropped images
    │   ├── slide3_method_crop.png
    │   └── slide5_results_crop.png
    ├── slide_01.html
    ├── slide_02.html
    ├── ...
    └── summary.md          ← final summary document
```

- `<pdf_stem>` = PDF filename without extension
- `<timestamp>` = format `YYYYMMDD_HHMMSS` (e.g. `20240119_143022`)
- Cropped images go in `crops/` subfolder
- Each slide HTML references images via relative path `crops/<name>.png`

## Input

`$ARGUMENTS` is the path to the PDF file (local) or an HTTP/HTTPS URL.

- If user provides a **URL**: download with curl first, then convert
- If user provides a **local PDF path**: convert directly

---

## Workflow

### Phase 0 — Create Output Directory

Compute the output path:
```python
import os, datetime
pdf_stem = os.path.splitext(os.path.basename(pdf_path))[0]
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
out_dir = os.path.join(workspace, "ppt", f"{pdf_stem}_{timestamp}")
```

Create it immediately:
```bash
mkdir -p "<out_dir>/crops"
```

Record `out_dir` — use it for all subsequent phases.

---

### Phase 1 — Convert PDF Pages to Images (DPI 120)

If the input is a URL, download it first:
```bash
pdf_stem=$(basename "$ARGUMENTS" .pdf)
curl -L -o "/tmp/${pdf_stem}.pdf" "$ARGUMENTS"
```
Then convert (pass either the downloaded path or the original local path):
```bash
python {SKILL_DIR}/scripts/pdf_to_images.py "<pdf_path>" --dpi 120
```

Outputs JSON to stdout:
```json
[{"page": 1, "path": "/abs/path/page_001.png"}, ...]
```

Parse and store the full `page → path` map. These local paths are used for viewing pages and as `--path` input to `crop.py`.

---

### Phase 2 — Read All Pages in Order

View **all page images** sequentially before planning anything. Your goal here is pure understanding — absorb the full structure, content, figures, and arguments of the document.

While reading, note:
- What figures, charts, or tables appear on which pages
- The overall arc (intro → method → results → conclusion for papers; or logical structure for other doc types)
- Candidate visuals worth cropping for slides (page number + rough region)

Do NOT plan or write slides yet — just read and understand all pages first.

---

### Phase 3 — Plan Outline & Save outline.json

After reading all pages, plan 8–15 slides (adapt freely for non-academic documents).

| Slide | Typical purpose |
|-------|----------------|
| 1 | Title, authors, affiliation, venue/year |
| 2 | Motivation / Problem statement |
| 3 | Related Work (brief) |
| 4–N-2 | Method / Core contributions (one concept per slide) |
| N-1 | Results & Experiments |
| N | Conclusion & Future Work |

For each slide that needs a visual, identify:
- Which page it comes from (the local page path from Phase 1)
- A description of what the visual shows and why it belongs on this slide

**Save the outline as `<out_dir>/outline.json`** using exactly this schema:

```json
{
  "presentation_title": "Paper Title Here",
  "lang": "Chinese",
  "total_slides": 10,
  "slides_plan": [
    {
      "slide_index": 1,
      "title": "Slide Title",
      "main_content": "Key points and text content for this slide",
      "template_id": null,
      "required_crops": [
        {
          "url": "<page_image_url_from_phase1>",
          "visual_description": "Figure 3: architecture diagram showing encoder-decoder",
          "usage_reason": "Illustrates the core model structure for slide 4"
        }
      ]
    }
  ]
}
```

Field notes:
- `lang`: `"Chinese"` or `"English"` — match the PDF language
- `template_id`: always `null`
- `required_crops`: empty array `[]` if this slide needs no images
- `url` in each crop: the **local file path** of the source page image (from Phase 1 `path` field) — this is what crop.py will open and crop from
- `visual_description`: what the visual shows, including figure/table number if available
- `usage_reason`: why this visual belongs on this particular slide

- For images that need cropping, note the approximate region — exact crop boxes are determined in Phase 4

Write `outline.json` using the Write tool to `<out_dir>/outline.json`.

---

### Phase 4 — Crop Required Images (Grounding + Subagent)

**IMPORTANT: You MUST delegate ALL cropping to a clean subagent using the Agent tool.** By this phase your context is very long (all page images + outline), which degrades visual coordinate accuracy. A fresh subagent with only the target image produces much more precise coordinates.

**IMPORTANT: You MUST use the provided `{SKILL_DIR}/scripts/crop.py` script for ALL image cropping. Do NOT write your own cropping code, do NOT use PIL/Pillow directly, do NOT use any other method.**

Read `outline.json`. Collect all crops needed, then launch **one subagent per source page** (or one per crop if pages differ). The subagent uses **grounding-style localization** — it views the image, locates the target element, and outputs a precise bounding box in normalized 0–999 coordinates.

Use the Agent tool like this:

```
Agent tool call:
  description: "Grounding crop page N"
  prompt: |
    You are a visual grounding and cropping assistant. Your task is to precisely
    locate specified visual elements in a page image and crop them out.

    ## Grounding method

    Use visual grounding to locate each target:
    1. Read the source image using the Read tool to view it
    2. Identify the target element described below
    3. Determine its bounding box as normalized coordinates in the 0–999 range:
       - 0 = left/top edge of the image
       - 999 = right/bottom edge of the image
       - These are thousandths, NOT pixels, NOT percentages (0–100)
       - Format: [x1, y1, x2, y2] where (x1,y1) is top-left, (x2,y2) is bottom-right
       - Example: [0, 0, 500, 500] = top-left quarter of the image
    4. Be precise: tightly bound the target element with a small margin (~10–20 units)
       around it. Do NOT crop too wide or too narrow.

    ## Source image
    <page_image_path>

    ## Crops needed

    For each crop below, first do grounding (locate the element), then crop:

    1. Name: "slide<N>_<descriptive_name>"
       Target: "<visual_description from outline.json>"
       Context: "<usage_reason from outline.json>"

    ## Crop command

    After determining the bounding box [X1, Y1, X2, Y2] for each target, run:
    ```bash
    python <SKILL_DIR>/scripts/crop.py \
        --path "<page_image_path>" \
        --box X1 Y1 X2 Y2 \
        --name "<crop_name>" \
        --out-dir "<out_dir>/crops"
    ```

    ## Verification

    After each crop, READ the output image to visually verify the correct region
    was captured. If the crop missed the target or is too wide/narrow, adjust the
    coordinates and re-run crop.py.

    ## Output

    Report the final results as a list:
    - crop_name: <name>, file: <output_filename>, box: [X1, Y1, X2, Y2]
```

Replace `<page_image_path>`, `<SKILL_DIR>`, `<out_dir>`, and crop details with actual values from your context.

The crop.py script outputs JSON: `{"path": "/abs/path/slide3_method_crop.png"}`

Collect results from all subagents and build the mapping: `slide_index → [crop filename, ...]` to reference in HTML. The filename will be `<name>_crop.png`.

**Launch subagents for independent pages in parallel** when possible. Wait for all to complete before proceeding.

---

### Phase 5 — Measure Cropped Image Dimensions

After cropping, get pixel dimensions:

```bash
python3 -c "
from PIL import Image; import os, json
d = '<out_dir>/crops'
sizes = {}
for f in sorted(os.listdir(d)):
    if f.endswith('.png'):
        w, h = Image.open(os.path.join(d, f)).size
        sizes[f] = {'width': w, 'height': h, 'aspect': round(w/h, 2)}
print(json.dumps(sizes, indent=2))
"
```

Use aspect ratios to pick each slide's layout:

| Aspect ratio | Layout recommendation |
|---|---|
| **< 0.7** (tall/narrow) | `text + image` side-by-side — `max-height: 600px` on image |
| **0.7 – 1.3** (square-ish) | `text + image` — image takes ~50% width |
| **> 1.3** (wide) | Image on top or bottom, text above/below |
| **> 2.0** (very wide, e.g. tables) | `full-image` — spans full 1280px width, caption below |

---

### Phase 6 — Generate Slides One by One

For each slide, write the HTML, save it to a temp file, then call `generate_slide.py`.

**Step A — Write HTML** to `/tmp/slide_N.html`

- All `<img src="...">` must use **relative paths**: `crops/<name>_crop.png`
- Do NOT use absolute paths or URLs for cropped images
- Navigation is click-area based — no buttons needed:
  - Clicking the **left half** of the slide navigates to the previous slide
  - Clicking the **right half** of the slide navigates to the next slide
  - On slide 1, left click does nothing; on the last slide, right click does nothing
  - Keyboard `←` / `→` arrows also navigate
  - Implement with two transparent `<div>` overlays covering each half, positioned absolute over the slide canvas

**Step B — Save slide:**
```bash
python {SKILL_DIR}/scripts/generate_slide.py \
    --html-file /tmp/slide_N.html \
    --index N \
    --total <total> \
    --title "<presentation title>" \
    --out-dir "<out_dir>/"
```

Repeat until all slides are saved.

---

### Phase 7 — Generate summary.md

Write `<out_dir>/summary.md` in the same language as the slides (`lang` from `outline.json`).

Include:
- Document title and basic info (authors, venue, year if applicable)
- Brief abstract/overview (2–3 sentences)
- Per-slide breakdown table: slide number, title, 1–2 sentence summary
- Main contributions or takeaways (bullet list)
- Link to `slide_01.html` to open the first slide

Example structure:
```markdown
# [Presentation Title]

> **来源 / Source:** [PDF filename] | **语言 / Language:** Chinese | **幻灯片数 / Slides:** 10

## 摘要
[2-3 sentence overview]

## 幻灯片概览
| # | 标题 | 主要内容 |
|---|------|---------|
| 1 | 标题页 | ... |
...

## 主要贡献
- ...

## 📂 打开演示文稿
[▶ 开始播放](slide_01.html)
```

---

## HTML Slide Spec

Each slide is a **standalone HTML file** — full `<html>…</html>` with embedded CSS only.

**Canvas:** fixed `1280 × 720 px`, `overflow: hidden` — nothing scrolls.

**Consistent design across all slides:**
- Choose a visual style that fits the document's domain and tone — no fixed palette or font required
- If the user specifies a style, follow it exactly; otherwise infer from the content (e.g. a ML paper → clean modern; a historical report → editorial serif; a product pitch → bold and branded)
- Same fonts, colors, and spacing system applied uniformly to every slide
- Every slide shows: slide title, page counter (bottom-right corner), presentation title (subtle footer)

**Navigation on each slide:**
- Two transparent click areas cover the full slide height: left 50% → previous slide, right 50% → next slide
- On slide 1 the left area is inert; on the last slide the right area is inert
- Keyboard `←` / `→` arrows also navigate
- No visible buttons needed — optionally show a subtle `‹` / `›` hint at the edges that fades in on hover

**Layout patterns:**
- `title-card` — centered hero, large title, authors/venue below
- `text-only` — structured bullet points, max 5–6 items, generous whitespace
- `text + image` — image right or left, text opposite
- `full-image` — image fills canvas, minimal text overlay
- `grid` — 2×2 or 3-column figures with captions

**Images:**
- Use relative paths: `crops/<name>_crop.png`
- Add `style="object-fit: contain; max-width: 100%; max-height: 100%;"`
- Add captions below in small italic text

**Do NOT:**
- Use external JS frameworks or icon CDNs
- Use placeholder/stock images — only the cropped PDFs
- Generate generic purple-gradient-on-white slides
- Let content overflow the 720px height

---

## Quality Checklist

- [ ] Output directory named `<pdf_stem>_<timestamp>/`
- [ ] `outline.json` saved with valid SlidesPlan schema
- [ ] All crops saved to `crops/` (local only, no cloud upload)
- [ ] Each slide fits within 1280×720, nothing overflows
- [ ] Consistent theme across all slides
- [ ] Crop images referenced via relative path `crops/<name>_crop.png`
- [ ] Slide number and presentation title visible on every slide
- [ ] Left/right click-area navigation works, keyboard arrows work
- [ ] `summary.md` written in the correct language, links to `slide_01.html`

---

## Language

Match the PDF language. Chinese PDF → Chinese slides and summary. English → English. No mixing.
