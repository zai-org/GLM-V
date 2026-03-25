---
name: glmv-grounding
description: >
  A skill that uses GLM-V native grounding capabilities for coordinate conversion,
  bounding-box visualization, and more. GLM-V native grounding can locate any target
  specified by the prompt in an image and output relative coordinates normalized to
  0-1000 based on image size. Coordinate formats include 2D bounding box (default),
  2D points, and 3D bounding box. GLM-V also supports spatiotemporal localization and
  tracking of multiple prompt-specified targets in videos, outputting 2D bounding boxes
  per second.
metadata:
  openclaw:
    requires:
      env:
        - ZHIPU_API_KEY
        - GLM_GROUNDING_TIMEOUT
      bins:
        - python
        - ffmpeg
    primaryEnv: ZHIPU_API_KEY
    emoji: "🖼️"
    source: https://github.com/zai-org/GLM-V/tree/main/skills/glmv-grounding
    homepage: https://github.com/zai-org/GLM-V/tree/main/skills/glmv-grounding
---

# GLMV-Grounding Skill

Extract and visualize grounding results produced by GLM-V. Depending on the user prompt, grounding coordinates in model outputs may appear in different forms, including 2D bounding boxes, Objects Detection JSON, 2D points, 3D bounding boxes, and target-tracking JSON.

**Note**: GLM-V outputs coordinates where **x and y are relative coordinates normalized from pixel coordinates x_pixel and y_pixel using image width W and height H (range 0-1000), i.e., x=round(x_pixel/W*1000), y=round(y_pixel/H*1000)**. The origin of the pixel coordinate system is the top-left corner.
**Note**: If the prompt does not explicitly specify a grounding format (for example, "find the location of xxx" or "draw a box around xxx"), treat the request as 2D bounding boxes by default.

## When to use

- **Use GLM-V to ground targets in images**: obtain grounding results in an image for any prompt-described target, with output formats such as 2D bounding box (default), 2D points, and 3D bounding box.
- **Use GLM-V to track targets in videos**: obtain tracking results in a video for any prompt-described target, with output format like {"0": [{"label": ..., "bbox_2d": ...}, ...], ...}.
- **Use utility functions for extraction, conversion, and visualization**: extract coordinates, points, and JSON from natural text; normalize and de-normalize coordinates; visualize boxes, points, 3D boxes, and video tracking results.

## Setup your API Key

Configure ZHIPU_API_KEY to call the GLM-V API.

1. Get your API key: https://www.bigmodel.cn/usercenter/proj-mgmt/apikeys
2. Configure it with:

```
python scripts/config_setup.py setup --api-key YOUR_KEY
```

## Security & Transparency

- **Primary API key env**: `ZHIPU_API_KEY` (required).
- **Timeout env**: `GLM_GROUNDING_TIMEOUT` (optional, seconds, default `60`).
- **API endpoint**: fixed to official Zhipu Chat Completions endpoint in CLI implementation.
- **No dynamic key name switching**: the skill expects `ZHIPU_API_KEY` consistently.
- **URL/local file handling**: the skill can read local files or fetch user-provided URLs for processing/visualization; URL inputs are restricted to public http/https targets (localhost/private network targets are rejected).

## Runtime Dependencies

Install dependencies before use:

```bash
pip install -r scripts/requirements.txt
```

Main packages used by this skill:

- `requests`
- `Pillow`
- `opencv-python`
- `numpy`
- `matplotlib`
- `decord`

System dependency for video visualization:

- `ffmpeg`

## General workflow

```
	Input (image or video + Prompt)
		|
		▼
	Run glm_grounding_cli.py to get grounding results (natural language)
		|
		▼
	Return results (grounding results, visualized image or video)
```

## How to Use

### Run glm_grounding_cli.py to get grounding results

- Ground any target in an image

```
python scripts/glm_grounding_cli.py --image-url "URL provided by user" --prompt "description of target for grounding"
```

- Track any target in a video

```
python scripts/glm_grounding_cli.py --video-url /path/to/image.jpg --prompt "description of target for tracking" --visualize --visualization-dir "./vis"
```

### Reply with grounding results

After receiving a grounding prompt from the user, your direct reply should be natural language that includes grounding coordinates. Coordinates $x$ and $y$ are relative values in [0, 1000], computed as:

$$
x = round(x_{pixel} / W * 1000) \\
y = round(y_{pixel}/H*1000)
$$

where $x_{pixel}, y_{pixel}$ are pixel coordinates with origin (0, 0) at the top-left corner of the image, and W/H are the image width/height.

**Unless otherwise specified, grounding results should use the following Python data formats**:

- _2D bounding boxes_: `[[x1, y1, x2, y2], ...]`, extracted grounding result is a list of boxes, each box has 4 coordinate values
- _2D points_: `[[x, y], ...]`, extracted grounding result is a list of points, each point has 2 coordinate values
- _2D polygon_: `[[x1, y1], [x2, y2], ...]`, extracted grounding result is a polygon coordinate list, each vertex has 2 coordinate values
- _3D bounding boxes_: `[{"bbox_3d":[x_center, y_center, z_center, x_size, y_size, z_size, roll, pitch, yaw],"label":"category"}, ...]`, extracted grounding result is a JSON list where each object contains a category label and one 3D box with 8 coordinate values
- _Objects Detection JSON_: `[{'label': 'category', 'bbox_2d': [x1, y1, x2, y2]}, ...]`, extracted grounding result is a JSON list where each object contains a category label and one box
- _Video Objects Tracking JSON_: `{0: [{'label': 'car-1', 'bbox_2d': [1,2,3,4]}, {'label': 'car-2', 'bbox_2d': [2,3,4,5]}], 1: [{'label': 'car-2', 'bbox_2d': [4,5,6,7]}, {'label': 'person-1', 'bbox_2d': [10,20,30,40]}]}`, extracted grounding result is a JSON object whose keys are video frame indices and values are lists of JSON objects, each containing a category label and one 2D box

## Python example

```shell

# 1. User grounding request and your reply
image=https://example.com/image.jpg
prompt="Please box all people wearing Santa hats in the image and tell me their coordinates. Use red boxes, line thickness 3, and label format 'SantaHat-i'."


# 2. Get grounding results
python scripts/glm_grounding_cli.py --image-url $image --prompt $prompt --visualize --visualization-dir "./vis"

#  {
#         "ok": True,
#         "grounding_result": [[100, 200, 300, 400], [500, 600, 700, 800]],
#         "visualizations_result": (
#             {"visualized_image": "./vis/image_vis.jpg"}
#         ),
#         "raw_result": "1. Person 1: box [100, 200, 300, 400]\n2. Person 2: box [500, 600, 700, 800]. The box format is [x1, y1, x2, y2], where (x1, y1) is the top-left corner and (x2, y2) is the bottom-right corner.",
#         "error": None,
#         "source": source,
#     }

```

## Utility function quick reference

| Function                                                                                                                                                                                                | Purpose                                                                                                       |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `parse_coordinates_from_response(response_str, coords_type='bbox', init_context_window=2000, max_context_window=-1)`                                                                                    | Parse and extract all coordinate results from model responses (supports 2D bbox, point, polygon)              |
| `parse_3d_boxes_from_response(response_str, max_context_window=-1)`                                                                                                                                     | Parse and extract all 3D boxes and labels from model responses (strict and loose matching)                    |
| `parse_detection_from_response(response_str, max_context_window=-1)`                                                                                                                                    | Parse and extract all 2D detection results from model responses (Objects Detection JSON format)               |
| `parse_mot_from_response(response_str, max_context_window=-1)`                                                                                                                                          | Parse and extract all video object tracking results from model responses (Video Objects Tracking JSON format) |
| `visualize_boxes(img_path=None, img_bytes=None, boxes=[], labels=None, renormalize=False, save_path=None, return_b64=False, save_optimized=True, **kwargs)`                                             | Draw 2D boxes on images with labels, custom colors, and line thickness                                        |
| `visualize_points(img_path=None, img_bytes=None, points=[], labels=None, renormalize=False, diameters=None, save_path=None, return_b64=False, save_optimized=True, distinct_colors=False, colors=None)` | Draw points on images with labels, custom size, and colors                                                    |
| `visualize_3d_boxes_glmv_simple(image_path, cam_params, bbox_3d_list, image_bytes=None, coord_format='xyzwhlpyr', save_path=None, save_optimized=False, return_b64=False, **kwargs)`                    | Draw projected 3D boxes on images using camera intrinsics (supports rotation and multiple coordinate formats) |
| `visualize_mot(video_path=None, video_bytes=None, mot_js=None, renormalize=False, save_path=None, return_b64=False, distinct_colors=True, **kwargs)`                                                    | Draw Video Objects Tracking boxes on each video frame with labels                                             |

## Common errors

- **Coordinate values exceed 1000**: if extracted coordinate values are greater than 1000, the model may have produced unnormalized coordinates due to prompt effects. Extract the target phrase from the user request (for example, "people wearing Santa hats"), then query the model again and explicitly require output coordinates to be relative values normalized to 0-1000 based on image size (for example, "Please box all people wearing Santa hats in the image and tell me their coordinates. Ensure the output coordinates are relative values normalized to 0-1000 based on image size.").
