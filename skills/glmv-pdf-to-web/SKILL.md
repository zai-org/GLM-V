---
name: glmv-pdf-to-web
description:
  Convert a PDF (research paper, technical report, or project document) into a beautiful
  single-page academic/project website with a structured outline JSON. Trigger this
  skill when the user wants to make a paper page, project homepage, or academic website
  from a PDF — in Chinese or English.
metadata:
  openclaw:
    requires:
      bins:
        - python
    emoji: "🌐"
    homepage: https://github.com/zai-org/GLM-V/tree/main/skills/glmv-pdf-to-web
---

# PDF → Academic Project Website Skill

Convert a research paper or technical document PDF into a polished single-page project website — the kind used for NeurIPS/CVPR/ICLR paper releases. Pages are converted locally at DPI 120, a structured `outline.json` is saved, images are cropped locally, and the final page is saved with `generate_web.py`.

**Scripts are in:** `{SKILL_DIR}/scripts/`

## Dependencies

Python packages (install once):
```bash
pip install pymupdf pillow
```

System tools: `curl` (pre-installed on macOS/Linux).

## When to Use

Trigger when the user asks to create a webpage or project page from a PDF — phrases like:
"make a project page from a PDF", "create a paper website", "build an academic website for this paper", "论文主页", "做项目主页", "根据pdf做网页", "把论文做成主页", or any similar intent in Chinese or English.

## Output Directory Convention

All output goes under `{WORKSPACE}/web/<pdf_stem>_<timestamp>/`:

```
web/
└── <pdf_stem>_<timestamp>/
    ├── outline.json        ← structured web plan (WebPlan schema)
    ├── crops/              ← locally-saved cropped images
    │   ├── fig_arch_crop.png
    │   ├── table_results_crop.png
    │   └── ...
    └── index.html          ← the website
```

- `<pdf_stem>` = PDF filename without extension
- `<timestamp>` = format `YYYYMMDD_HHMMSS`
- HTML references images via relative path `crops/<name>_crop.png`

## Input

`$ARGUMENTS` is the path to the PDF file (local) or an HTTP/HTTPS URL.

- If user provides a **URL**: download with curl first, then convert
- If user provides a **local PDF path**: convert directly

---

## Workflow

### Phase 0 — Create Output Directory

```python
import os, datetime
pdf_stem = os.path.splitext(os.path.basename(pdf_path))[0]
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
out_dir = os.path.join(workspace, "web", f"{pdf_stem}_{timestamp}")
```

```bash
mkdir -p "<out_dir>/crops"
```

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

Parse and store the full `page → path` map.

---

### Phase 2 — Read All Pages in Order

View **all page images** sequentially before planning. Goal: pure understanding of the document's content, figures, and structure.

While reading, note:
- Title, authors, affiliations, venue, year
- Abstract text (verbatim)
- Key contributions
- Paper/Code/Dataset links (arXiv, GitHub, etc.)
- Figures, tables, diagrams — which pages, rough regions
- Teaser/hero figure if present

Do NOT plan sections yet — read everything first.

---

### Phase 3 — Plan Sections & Save outline.json

Plan the website sections. Standard structure for academic papers (adapt as needed):

| `section_id` | Purpose |
|---|---|
| `hero` | Title, authors, venue badge, link buttons |
| `abstract` | Full abstract text |
| `contributions` | 3–5 key contribution cards |
| `method` | Architecture figure + method explanation |
| `results` | Quantitative table + qualitative figures |
| `conclusion` | Brief conclusion |
| `citation` | BibTeX block |

For each section that needs an image, identify:
- Which page it comes from (the local page path from Phase 1)
- A description of what the visual shows and why it belongs in this section

**Save as `<out_dir>/outline.json`** using exactly this schema:

```json
{
  "project_title": "Paper Title",
  "lang": "English",
  "authors": ["Author One", "Author Two"],
  "sections_plan": [
    {
      "section_index": 1,
      "section_id": "hero",
      "title": "Hero",
      "content": "Title, authors, venue, teaser figure description",
      "required_images": [
        {
          "url": "<local_page_path_from_phase1>",
          "visual_description": "Figure 1: teaser showing input-output examples",
          "usage_reason": "Hero section visual to immediately show the paper's output"
        }
      ]
    }
  ]
}
```

Field notes:
- `lang`: `"Chinese"` or `"English"` — match the PDF language
- `required_images`: empty array `[]` if section needs no images
- `url`: the **local file path** of the source page (from Phase 1 `path` field)
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

    1. Name: "<descriptive_name>"
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

The crop.py script outputs JSON: `{"path": "/abs/path/<name>_crop.png"}`

Collect results from all subagents and build the mapping: `section_id → [crop filename, ...]` to reference in HTML.

**Launch subagents for independent pages in parallel** when possible. Wait for all to complete before proceeding.

---

### Phase 5 — Measure Cropped Image Dimensions

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

| Aspect ratio | Layout recommendation |
|---|---|
| **< 0.7** (tall/narrow) | `max-width: 400–500px`, centered |
| **0.7 – 1.3** (square-ish) | `max-width: 600–700px` |
| **> 1.3** (wide) | Full-width, `max-width: 100%` |
| **> 2.0** (very wide, e.g. tables) | Full-width with horizontal scroll fallback |

---

### Phase 6 — Generate the Single-Page HTML

**Step A — Write HTML** to `/tmp/website.html`

- All `<img src="...">` must use **relative paths**: `crops/<name>_crop.png`
- Do NOT use absolute paths

**Step B — Save:**
```bash
python {SKILL_DIR}/scripts/generate_web.py \
    --html-file /tmp/website.html \
    --title "<paper title>" \
    --out-dir "<out_dir>/"
```

---

## HTML Spec

A **single self-contained HTML file** — embedded CSS, minimal vanilla JS only. No external JS frameworks. Google Fonts CDN is fine.

**Page layout:**
- Max content width: `900px`, centered, comfortable side padding
- Sticky top nav with section anchor links + smooth scroll
- Looks good at 1200px wide; readable at 768px

**Typography:**
- Two Google Fonts: one for headings, one for body/UI
- Body: 17–18px, line-height 1.7
- Strong heading hierarchy (h1 >> h2 >> h3)

**Visual style:**
- If the user specifies a style, follow it exactly
- Otherwise, infer an appropriate aesthetic from the paper's domain and tone (e.g. CV/ML paper → clean modern academic; systems paper → dark technical; humanities → warm editorial serif)
- Define colors and fonts as CSS variables; no fixed palette or font choices are required

**Section guidelines:**

`hero`:
- Large title (2–3rem), authors list with affiliation superscripts, venue badge pill
- Link buttons: `[📄 Paper] [💻 Code] [🗄️ Dataset]` — grey out if no URL
- Teaser figure below (if found)

`abstract`:
- Verbatim text with subtle left border accent

`contributions`:
- Cards in a 2–3 column CSS grid, each with Unicode symbol + heading + description

`method`:
- Full-width architecture figure (`<figure><img><figcaption>`) + prose explanation

`results`:
- **Quantitative table** as real `<table>` — use actual numbers from the PDF, best numbers **bolded**
- **Qualitative figures** in a grid (2–4 images with captions)

`conclusion`:
- 2–3 paragraphs

`citation`:
- `<pre><code>` BibTeX block reconstructed from PDF metadata
- "Copy" button using `navigator.clipboard` vanilla JS

**Images:**
- All `<img>` use relative paths: `crops/<name>_crop.png`
- Add `loading="lazy"` and descriptive `alt`
- Wrap in `<figure>` with `<figcaption>`

**Animations (subtle only):**
- Fade-in on scroll via `IntersectionObserver` + CSS transitions
- Hover states on buttons/cards

---

---

## Quality Checklist

- [ ] Output directory named `<pdf_stem>_<timestamp>/`
- [ ] `outline.json` saved with valid WebPlan schema
- [ ] All crops saved to `crops/` (local only)
- [ ] All metadata (title, authors, venue, year) from the PDF
- [ ] Abstract is verbatim
- [ ] Quantitative table has real numbers from the paper
- [ ] All crop images referenced via `crops/<name>_crop.png`
- [ ] BibTeX block accurate and copyable
- [ ] Nav anchors scroll to correct sections
- [ ] `generate_web.py` called and confirmed success

---

## Language

Match the PDF language. English paper → English website. Chinese paper → Chinese. No mixing.
