import base64, cv2, io, os, math, tempfile, re, json, ast, shutil, subprocess, glob
import numpy as np
from pathlib import Path
from decord import VideoReader, cpu
import matplotlib.pyplot as plt
import traceback
import colorsys
from PIL import Image
from ast import literal_eval


def _to_number(x):
    if isinstance(x, (int, float)):
        return x
    if isinstance(x, str):
        x = x.strip()
        if not x:
            return None
        try:
            return float(x) if ("." in x or "e" in x.lower()) else int(x)
        except Exception:
            return None
    return None


def reverse_normalize_box(
    box, img_width=None, img_height=None, img_path=None, round_fn=lambda x: round(x, 2)
):
    if img_path is not None:
        with Image.open(img_path) as img:
            img_width, img_height = img.size
    box = [max(0, min(x, 999)) for x in box]
    box = [x / 1000.0 for x in box]
    # box = [box[0] * im_width, box[1] * img_height, box[2] * im_width, box[3] * img_height]
    box = [
        box[_] * img_width if _ % 2 == 0 else box[_] * img_height
        for _ in range(len(box))
    ]
    box = [round_fn(x) for x in box]  # round to 2 decimal places
    return box


def get_distinct_colors_hsv(n, bright=True, normalize=True):
    """
    Generate random colors.
    To get visually distinct colors, generate them in HSV space then
    convert to RGB.
    """
    brightness = 1.0 if bright else 0.7
    hsv = [(i / n, 1, brightness) for i in range(n)]
    colors = list(map(lambda c: colorsys.hsv_to_rgb(*c), hsv))
    if not normalize:
        colors = [(int(r * 255), int(g * 255), int(b * 255)) for r, g, b in colors]
    # random.shuffle(colors)
    return colors


def video_to_base64(video_path):
    with open(video_path, "rb") as video_file:
        # 读取视频文件并转换为 Base64 编码的字节数据
        encoded_string = base64.b64encode(video_file.read())
        return encoded_string.decode("utf-8")


def build_video_from_frames(
    frames: np.ndarray = None,
    frames_paths: str = None,
    output_path=None,
    fps=1,
    return_bytes=False,
):
    """Build video from frames.
    @frames: List of frames as numpy arrays.
    @frames_paths: List of frame file paths.
    """
    assert frames or frames_paths, "Either frames or frames_paths must be provided."
    if frames is None:
        frames = []
        for frame_path in frames_paths:
            frame = cv2.imread(frame_path)
            frames.append(frame)
    height, width, _ = frames[0].shape

    if output_path is None:
        output_temp = tempfile.NamedTemporaryFile(suffix=".mp4")
        output_path = output_temp.name

    # fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fourcc = cv2.VideoWriter_fourcc(*"H264")
    video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    for idx, frame in enumerate(frames):
        if frame is None:
            print(f"Frame at index {idx} is None, skipping.")
            continue
        if len(frame.shape) == 2:  # grayscale to BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif frame.shape[2] == 4:  # RGBA to BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
        video_writer.write(frame)
    video_writer.release()
    print(f"✅ Video saved to {output_path}")

    # delete temp file if used
    if "output_temp" in locals():
        output_temp.close()

    if return_bytes:
        with open(output_path, "rb") as f:
            video_bytes = f.read()
        return video_bytes
    else:
        return output_path


def visualize_mot(
    video_path: str = None,
    video_bytes=None,
    mot_js=None,
    renormalize=True,
    save_path: str = None,
    return_b64=False,
    distinct_colors=True,
    **kwargs,
):
    """Visualize the mot results for a given video, where the format of mot_js should be {0: [{"label": xx, "bbox_2d": [x1,y1,x2,y2]}, ..], 1: ..} where the keys refer to the timestamp in seconds and values are detection results."""
    assert (
        video_path is not None or video_bytes is not None
    ), "Either video_path or video_bytes must be provided."
    assert mot_js is not None, "mot_js must be provided."

    label2colors = kwargs.get("label2colors", {})
    label2colors = {
        _k: tuple(int(c * 255) for c in plt.matplotlib.colors.to_rgb(_v))
        for _k, _v in label2colors.items()
    }
    label2thickness = kwargs.get("label2thickness", {})

    # --- Read original video
    if video_path is not None:
        vr = VideoReader(video_path, ctx=cpu(0))
    else:
        # video_bytes 情况：保存到临时文件再读取
        vr = VideoReader(io.BytesIO(video_bytes), ctx=cpu(0))
    fps, frame_count = vr.get_avg_fps(), len(vr)
    height, width = vr[0].shape[:2]

    output_path = save_path if save_path is not None else tempfile.mktemp(suffix=".mp4")

    # 定义 VideoWriter
    # writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    writer = cv2.VideoWriter(
        output_path, cv2.VideoWriter_fourcc(*"H264"), fps, (width, height)
    )
    if not writer.isOpened():
        print(f"Failed to open video writer for output_path: {output_path}")
        output_path = str(Path(output_path).with_suffix(".avi"))
        writer = cv2.VideoWriter(
            output_path, cv2.VideoWriter_fourcc(*"XVID"), fps, (width, height)
        )

    all_labels = set([_d["label"] for _f in mot_js for _d in mot_js[_f]])
    if distinct_colors:
        all_colors = get_distinct_colors_hsv(len(all_labels), normalize=False)
        label2colors = {str(_lbl): all_colors[_i] for _i, _lbl in enumerate(all_labels)}
    for frame_id in range(frame_count):
        frame = vr[frame_id].asnumpy()
        # 转成 RGB 方便绘制
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        annotated_frame = frame_rgb.copy()
        # dets = mot_js.get(frame_id, []) or mot_js.get(str(frame_id), [])  # 当前秒的所有检测结果
        if frame_id % fps == 0:
            dets = mot_js.get(str(math.floor(frame_id / fps)), []) or mot_js.get(
                str(math.floor(frame_id // fps)), []
            )  # 当前秒的所有检测结果
        else:
            dets = []
        labels = []
        boxes = []
        for det in dets:
            lbl = str(det.get("label", ""))
            box = det.get("bbox_2d", [])
            try:
                if renormalize:
                    box = reverse_normalize_box(box, width, height, round_fn=int)
                else:
                    box = [int(_) for _ in box]
            except:
                import traceback

                print(
                    f"Error in processing bbox for frame_id: {frame_id}, label: {lbl}"
                )
                traceback.print_exc()
            labels.append(lbl)
            boxes.append(box)
        # 绘制每个框和标签
        for box, lbl in zip(boxes, labels):
            cv2.rectangle(
                annotated_frame,
                box[:2],
                box[2:],
                color=label2colors.get(str(lbl), (0, 255, 0)),
                thickness=label2thickness.get(str(lbl), 2),
            )
            cv2.putText(
                annotated_frame,
                lbl,
                (box[0], box[1]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                label2colors.get(str(lbl), (0, 255, 0)),
                thickness=label2thickness.get(str(lbl), 2),
            )
        # 再转成 BGR 给cv2写视频
        # annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_RGB2BGR)
        writer.write(annotated_frame)
    writer.release()

    # return
    if return_b64:
        with open(output_path, "rb") as f:
            b64_video = base64.b64encode(f.read()).decode("utf-8")
        if save_path is None:
            os.remove(output_path)
        return b64_video
    else:
        return output_path


def visualize_mot_per_frame(
    video_path: str = None,
    video_bytes=None,
    mot_js=None,
    renormalize=True,
    save_path: str = None,
    distinct_colors=True,
    thickness=3,
    **kwargs,
):
    """Visualize MOT results on EVERY frame (not just 1 per second).

    Uses visualize_boxes to draw boxes on each extracted frame, then ffmpeg
    to reassemble at the original framerate. Much faster than visualize_mot
    which writes frames one-by-one via OpenCV.

    Args:
        video_path: Path to input video.
        video_bytes: Bytes of input video (alternative to video_path).
        mot_js: MOT results dict with STRING keys: {"0": [{"label": "cat-1", "bbox_2d": [x1,y1,x2,y2]}], "1": ...}
        renormalize: If True, convert 0~1000 normalized coords to pixel coords.
        save_path: Output video path.
        distinct_colors: If True, auto-generate distinct colors per label.
        thickness: Box line thickness.
        **kwargs: Passed to visualize_boxes (colors, labels, etc.)

    Returns:
        Output video path.
    """
    from utils_boxes import visualize_boxes

    assert (
        video_path is not None or video_bytes is not None
    ), "Either video_path or video_bytes must be provided."
    assert mot_js is not None, "mot_js must be provided."

    # --- Read video info ---
    if video_path is not None:
        vr = VideoReader(video_path, ctx=cpu(0))
    else:
        vr = VideoReader(io.BytesIO(video_bytes), ctx=cpu(0))
    fps = vr.get_avg_fps()
    frame_count = len(vr)
    height, width = vr[0].shape[:2]

    # --- Ensure string keys in mot_js ---
    mot_str = {}
    for k, v in mot_js.items():
        mot_str[str(k)] = v

    # --- Setup colors ---
    label2colors = kwargs.get("label2colors", {})
    if not label2colors and distinct_colors:
        all_labels = sorted(set(d["label"] for dets in mot_str.values() for d in dets))
        # Use matplotlib named colors for visualize_boxes compatibility
        named_colors = [
            "red",
            "blue",
            "green",
            "orange",
            "purple",
            "cyan",
            "magenta",
            "yellow",
            "lime",
            "pink",
        ]
        label2colors = {
            lbl: named_colors[i % len(named_colors)] for i, lbl in enumerate(all_labels)
        }

    # --- Extract all frames ---
    tmp_dir = tempfile.mkdtemp(prefix="mot_viz_")
    raw_dir = os.path.join(tmp_dir, "raw")
    out_dir = os.path.join(tmp_dir, "out")
    os.makedirs(raw_dir)
    os.makedirs(out_dir)

    if video_path is not None:
        # Extract all frames
        raw_pattern = os.path.join(raw_dir, "frame_%05d.jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-q:v", "2", raw_pattern],
            capture_output=True,
        )
    else:
        # Save bytes to temp file then extract
        tmp_video = os.path.join(tmp_dir, "input.mov")
        with open(tmp_video, "wb") as f:
            f.write(video_bytes)
        raw_pattern = os.path.join(raw_dir, "frame_%05d.jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_video, "-q:v", "2", raw_pattern],
            capture_output=True,
        )

    # --- Draw boxes on every frame ---
    frame_files = sorted(glob.glob(os.path.join(raw_dir, "frame_*.jpg")))
    total_frames = len(frame_files)

    for i, f in enumerate(frame_files):
        sec_idx = str(
            min(int(i / fps), max(int(k) for k in mot_str.keys()) if mot_str else 0)
        )
        dets = mot_str.get(sec_idx, [])
        if not dets:
            # Try neighboring seconds
            for offset in [-1, 1]:
                alt = str(int(sec_idx) + offset)
                if alt in mot_str:
                    dets = mot_str[alt]
                    break

        if dets:
            boxes = [d["bbox_2d"] for d in dets]
            labels = [d["label"] for d in dets]
            colors = [label2colors.get(lbl, "red") for lbl in labels]
            thicknesses = [thickness] * len(boxes)
            save_p = os.path.join(out_dir, f"frame_{i:05d}.jpg")
            visualize_boxes(
                img_path=f,
                boxes=boxes,
                labels=labels,
                renormalize=renormalize,
                save_path=save_p,
                colors=colors,
                thickness=thicknesses,
            )
        else:
            # No detections, copy original frame
            shutil.copy(f, os.path.join(out_dir, f"frame_{i:05d}.jpg"))

        if (i + 1) % 100 == 0:
            print(f"  visualize_mot_per_frame: {i+1}/{total_frames} frames done")

    # --- Reassemble with ffmpeg ---
    output_path = save_path if save_path else os.path.join(tmp_dir, "output.mp4")
    out_pattern = os.path.join(out_dir, "frame_%05d.jpg")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            out_pattern,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            output_path,
        ],
        capture_output=True,
    )

    # Cleanup temp dirs
    shutil.rmtree(tmp_dir, ignore_errors=True)

    print(
        f"✅ visualize_mot_per_frame: video saved to {output_path} ({total_frames} frames at {fps:.1f}fps)"
    )
    return output_path


def parse_detection_js(txt, match_all_keys=False):
    """Parse object detection results outputted by GLM-V, refer to https://zhipu-ai.feishu.cn/wiki/PxWtwH1rziRh1mkdcsvcgghinyg.
    The valid format should include keys of `label`, `bbox_2d` with values of label-name and detection-bbox (e.g., {'label':'person-1', 'bbox_2d': [1,2,3,4]}).
    """
    # 1. define kv match patterns & kv valid map
    kv_pattern = {
        "label": (
            r"[\'\"]label[\'\"]\s*:\s*[\"\']",
            r"(.*?)",
            r"[\"\'][,\s]+",
        ),  # (pre, mid, post)
        "bbox_2d": (
            r"[\'\"]bbox_2d[\'\"]\s*:\s*",
            r"(\[\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\])",
            ".*",
        ),
        "bbox_3d": (
            r"[\'\"]bbox_3d[\'\"]\s*:\s*",
            r"(\[\s*-*\d+\.*\d+\s*,\s*-*\d+\.*\d+\s*,\s*-*\d+\.*\d+\s*,\s*-*\d+\.*\d+\s*,\s*-*\d+\.*\d+\s*,\s*-*\d+\.*\d+\s*,\s*-*\d+\.*\d+\s*,\s*-*\d+\.*\d+\s*,\s*-*\d+\.*\d+\s*\])",
            ".*",
        ),
    }
    kv_to_valid = {
        "label": lambda x: str(x) if x else "",
        "bbox_2d": lambda x: (
            [int(_) for _ in literal_eval(str(x))]
            if re.search(kv_pattern["bbox_2d"][1], str(x))
            else []
        ),
        "bbox_3d": lambda x: (
            [float(_) for _ in literal_eval(str(x))]
            if re.search(kv_pattern["bbox_3d"][1], str(x))
            else []
        ),
    }

    valid_js, match_js = {}, {}
    # 2. parse valid json
    try:
        _js = literal_eval(txt)
        if isinstance(_js, dict):
            for k, v in _js.items():
                valid_js[k] = kv_to_valid.get(k, lambda x: x)(v)
    except:
        pass
    # 3. fallback to match
    try:
        for m in re.finditer(
            r"[\"\']*(\w+)[\"\']*\s*:\s*[\"\']*([^\{\}\[\],\"\']+|[\{\[][^{}]*?[\}\]])[\"\']*",
            txt,
        ):  # match "key": value or 'key': value, where value can be a primitive or a list/dict, and strip quotes from string values
            k, v = m.groups()
            match_js[k] = kv_to_valid.get(k, lambda x: x)(v.strip())
        # for k, ptrs in kv_pattern.items():
        #     found = re.search(''.join(ptrs), txt)
        #     if found:
        #         match_js[k] =  kv_to_valid.get(k, lambda x:x)(found.group(1))
    except:
        pass
    # 3. check completeness for valid_js
    if match_all_keys:
        if not all([_ in valid_js for _ in kv_pattern.keys()]):
            valid_js = {}
    return valid_js, match_js


def parse_detection(txt, return_valid_only=False):
    """Extract a list of multiple detection results, where each det result refers to a JSON with 'label' and 'bbox_2d' keys."""
    valid_result, match_result = [], []
    if isinstance(txt, str):
        txt = txt.strip()
    # 1. parse valid detection strictly follow the format
    try:
        dets = literal_eval(txt)  # assume to be a list of dicts
        for d in dets:
            if isinstance(d, dict):
                d = json.dumps(d)
            valid_js, match_js = parse_detection_js(str(d))
            if valid_js:
                valid_result.append(valid_js)
    except:
        pass
    # 2. fallback to match
    try:
        dets = re.findall(r"\{[^{}]*\}", txt)
        for d in dets:
            valid_js, match_js = parse_detection_js(str(d))
            if valid_js:
                match_result.append(match_js)
    except:
        pass

    if return_valid_only:
        return valid_result
    return valid_result, match_result


def parse_detection_from_response(
    response_str, max_context_window=-1, required_keys=["bbox_2d"]
):
    """从模型回复文本中解析出Objects Detection JSON: `[{'label': 'category', 'bbox_2d': [x1, y1, x2, y2]}, ...]`，抽取出的grounding结果是一个JSON列表，每个JSON对象包含一个类别标签和一个4值坐标框。基本逻辑如下：
    - 解析出两个结果，一个是直接找到左、右括号字符，然后直接严格解析找到的字符串，作为strict_match结果；
    - 另一个是按括号匹配算法从后向前收集的结果，作为loose_match结果，匹配算法逻辑如下：
      + 从最后一个字符开始向前做栈式括号匹配算法，找到完整的[{"bbox_2d", [...]}, {}, ...]字符串。即从后向前查找，每逢右括号就入栈，每逢左括号就出栈，当匹配完整的JSON时（即{"bbox_2d": [...]})记录一个2D坐标框的字符串，直到找到最后一个完整的JSON字符串为止。这个过程可以确保即使坐标被截断了（如被分成两行输出），也能正确地找到完整的坐标字符串。当栈空或达到`max_context_window`时停止。

    最终，返回strict_match和loose_match。
    """

    def _iter_dets_text_candidates(s):
        """Linear-time extraction of complete [...] candidates containing bbox_2d."""
        stack = []
        for idx, ch in enumerate(s):
            if ch == "[":
                stack.append(idx)
            elif ch == "]" and stack:
                start = stack.pop()
                seg = s[start : idx + 1]
                if all(k in seg for k in required_keys) and "{" in seg:
                    yield seg

    def _is_valid_det(det):
        if not isinstance(det, dict):
            return False
        for k in required_keys:
            if k not in det:
                return False
            v = det.get(k)
            if v is None:
                return False
            if isinstance(v, (str, list, tuple, dict, set)) and len(v) == 0:
                return False
        return True

    # 防御式处理输入
    if not isinstance(response_str, str) or not response_str.strip():
        return [], []

    text = response_str
    if not all(k in text for k in required_keys):
        return [], []
    strict_match = []
    loose_match = []

    # ---------- strict_match ----------
    best = []
    for seg in _iter_dets_text_candidates(text):
        parsed = [
            d for d in parse_detection(seg, return_valid_only=True) if _is_valid_det(d)
        ]
        if parsed and len(parsed) > len(best):
            best = parsed
    strict_match = best

    # ---------- loose_match ----------
    # 从后向前，优先匹配“最右侧完整数组”，找不到再降级到对象级恢复。
    n = len(text)
    window = (
        n
        if (max_context_window is None or max_context_window < 0)
        else min(n, int(max_context_window))
    )
    start_limit = max(0, n - window)

    # Step 1: rightmost complete array
    sq_stack = []
    rightmost_array = []
    for i in range(n - 1, start_limit - 1, -1):
        ch = text[i]
        if ch == "]":
            sq_stack.append(i)
        elif ch == "[":
            if not sq_stack:
                continue
            j = sq_stack.pop()
            seg = text[i : j + 1]
            if not (all(k in seg for k in required_keys) and "{" in seg):
                continue
            parsed = [
                d
                for d in parse_detection(seg, return_valid_only=True)
                if _is_valid_det(d)
            ]
            if parsed:
                rightmost_array = parsed
                break

    if rightmost_array:
        loose_match = rightmost_array
    else:
        # Step 2: fallback object-level recovery (useful for truncated tail)
        obj_stack = []
        objs = []
        for i in range(n - 1, start_limit - 1, -1):
            ch = text[i]
            if ch == "}":
                obj_stack.append(i)
            elif ch == "{":
                if not obj_stack:
                    continue
                j = obj_stack.pop()
                seg = text[i : j + 1]
                if not (all(k in seg for k in required_keys) and "{" in seg):
                    continue
                valid_js, _ = parse_detection_js(seg)
                if _is_valid_det(valid_js):
                    objs.append(valid_js)
        if objs:
            loose_match = list(reversed(objs))

    return strict_match, loose_match


def parse_mot_from_response(
    response_str, max_context_window=256000, required_keys=["bbox_2d"]
):
    """从模型回复文本中解析出Video Objects Tracking JSON: `{"0": [{'label': 'car-1', 'bbox_2d': [1,2,3,4]}, {'label': 'car-2', 'bbox_2d': [2,3,4,5]}], '1': [{'label': 'car-2', 'bbox_2d': [4,5,6,7]}, {'label': 'person-1', 'bbox_2d': [10,20,30,40]}]}`, 抽取出的grounding结果是一个JSON对象，键为视频帧索引，值为一个列表，每个列表元素是一个JSON对象，包含一个类别标签和一个2D坐标框。基本逻辑：
    - 解析出两个结果，一个是直接找到左、右括号字符，然后直接严格解析找到的字符串，作为strict_match结果；s
    - 另一个从后向前找到每一个完整的以序号为key以object detectionJSON对象（即{"label": ..., "bbox_2d": [...]})为value的字符串，然后调用parse_detection_from_response的解析函数解析出detection结果，最终合成一个mot结果，作为loose_match结果。这个过程可以确保即使坐标被截断了（如被分成两行输出），也能正确地找到完整的坐标字符串。当栈空或达到`max_context_window`时停止。

    最终，返回strict_match和loose_match。
    """
    mot_pattern = r"[\"\']*(\d+)[\"\']*\s*\:\s*(\[\s*\{.*?\}\s*\])"

    def _normalize_frame_key(k):
        if isinstance(k, int):
            return str(k)
        if isinstance(k, str):
            kk = k.strip().strip('"').strip("'")
            if re.fullmatch(r"-?\d+", kk):
                return str(int(kk))
        return None

    def _sort_mot_keys(mot):
        return {k: mot[k] for k in sorted(mot, key=lambda x: int(x))}

    def _parse_det_value(v):
        if isinstance(v, str):
            s = v
        elif isinstance(v, (list, dict)):
            s = repr(v)
        else:
            return []
        strict_dets, loose_dets = parse_detection_from_response(
            s,
            max_context_window=-1,
            required_keys=required_keys,
        )
        return strict_dets or loose_dets

    def _normalize_mot_obj(obj):
        if not isinstance(obj, dict):
            return {}
        out = {}
        for k, v in obj.items():
            key = _normalize_frame_key(k)
            if key is None:
                continue
            dets = _parse_det_value(v)
            if dets:
                out[key] = dets
        return _sort_mot_keys(out)

    def _parse_mot_js(txt, strict_only=False):
        # 1) 先走结构化解析（更准确）
        for loader in (json.loads, ast.literal_eval):
            try:
                norm = _normalize_mot_obj(loader(txt.strip()))
                if norm:
                    return norm
            except:
                pass

        if strict_only:
            return {}

        # 2) 兜底正则（兼容半结构化文本）
        out = {}
        for m in re.finditer(mot_pattern, txt):
            res_tid, dets = m.groups()
            key = _normalize_frame_key(res_tid)
            if key is None:
                continue
            parsed = _parse_det_value(dets)
            if parsed:
                out[key] = parsed
        return _sort_mot_keys(out)

    def _iter_dets_text_candidates(s):
        """从后向前，仅在栈清空时产出顶层闭合块候选，避免内层{}反复正则。"""
        stack = []
        for idx in range(len(s) - 1, -1, -1):
            ch = s[idx]
            if ch == "}":
                stack.append(idx)
            elif ch == "{":
                if not stack:
                    continue
                end_idx = stack.pop()
                if stack:
                    continue
                seg = s[idx : end_idx + 1]
                if all(k in seg for k in required_keys) and re.search(mot_pattern, seg):
                    yield seg

    if not isinstance(response_str, str) or not response_str.strip():
        return {}, {}

    n = len(response_str)
    window = (
        n
        if (max_context_window is None or max_context_window < 0)
        else min(n, int(max_context_window))
    )
    text = response_str[-window:] if window > 0 else response_str

    strict_match, loose_match = {}, {}

    # === strict match ===
    try:
        for seg in _iter_dets_text_candidates(text):
            strict_match = _parse_mot_js(seg, strict_only=True)
            # 只找一个完整的MOT对象，找到后就
            break
    except:
        pass

    # === loose match ===
    for seg in _iter_dets_text_candidates(text):
        parsed_mot = _parse_mot_js(seg, strict_only=False)
        if parsed_mot and len(parsed_mot) > len(loose_match):
            loose_match = parsed_mot

    # return strict_match, loose_match
    return loose_match


if __name__ == "__main__":
    # 测试 parse_detection_from_response
    test_str = """
    Here are the detections: [{"label": "car", "bbox_2d": [100, 150, 200, 250]}, {"label": "person", "bbox_2d": [300, 350, 400, 450]}]
    And some more text.
    """
    loose = parse_detection_from_response(test_str)
    print("Loose:", loose)

    # 测试 parse_mot_from_response
    test_mot_str = """
    Tracking results: {0: [{"label": "car-1", "bbox_2d": [1,2,3,4]}, {"label": "car-2", "bbox_2d": [2,3,4,5]}], 1: [{"label": "car-2", "bbox_2d": [4,5,6,7]}, {"label": "person-1", "bbox_2d": xx}]}
    """
    loose_mot = parse_mot_from_response(test_mot_str)
    print("Loose MOT:", loose_mot)
