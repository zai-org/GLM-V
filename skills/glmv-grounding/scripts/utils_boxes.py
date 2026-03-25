#!/usr/bin/env python3
"""
本工具脚本包含：从模型的回复文本中解析坐标框，对坐标框做反向归一化，在图片上可视化画框等。
"""

import math, os, io, base64, json, ast, copy, numbers, bisect, re
from PIL import Image, ImageDraw, ImageFont
import cv2
from enum import Enum, auto
import numpy as np
import matplotlib.pyplot as plt
import colorsys


class BracketsStyle(Enum):
    """Enum for different styles of brackets."""

    SQUARE = {"left": "[", "right": "]"}  # []
    CURLY = {"left": "{", "right": "}"}  # {}
    ANGLE = {"left": "<", "right": ">"}  # <>
    PARENTHESES = {"left": "(", "right": ")"}  # ()
    BBOX = {"left": "<bbox>", "right": "</bbox>"}  # <bbox> </bbox>


class NestedStyle(Enum):
    """Enum for different styles of nested brackets."""

    DOUBLE = auto()  # [[]] or {{}}
    SINGLE = auto()  # [] or {}


def _safe_number(v):
    """Safely coerce scalar to number without eval."""
    if isinstance(v, numbers.Number):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        # Support simple fractional form like "1/2"
        if re.fullmatch(r"[+-]?\d+\s*/\s*[+-]?\d+", s):
            try:
                num, den = s.split("/", 1)
                den_v = float(den)
                if den_v == 0:
                    return None
                return float(num) / den_v
            except Exception:
                return None
        # Standard int/float parsing
        try:
            if re.fullmatch(r"[+-]?\d+", s):
                return int(s)
            return float(s)
        except Exception:
            return None
    return None


def _coerce_coord_list(lst):
    """Convert a list of coordinates to numeric values safely."""
    out = []
    for item in lst:
        n = _safe_number(item)
        if n is None:
            return None
        out.append(n)
    return out


def is_single_list(lst):
    if isinstance(lst, list) and (len(lst) == 0 or not isinstance(lst[0], list)):
        return True
    return False


def is_nested_list(lst):
    if isinstance(lst, list) and len(lst) > 0 and isinstance(lst[0], list):
        return True
    return False


def flat_boxes(boxes):
    res_boxes = []

    def _flat(lst):
        if not isinstance(lst, list) or len(lst) == 0:
            return
        elif not isinstance(lst[0], list):
            res_boxes.append(lst)
        else:
            for l in lst:
                _flat(l)

    _flat(boxes)
    return res_boxes


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


def find_coordinates(
    text,
    coords_type="bbox",
    brackets_style=BracketsStyle.SQUARE,
    nested_style=NestedStyle.SINGLE,
    return_matches=False,
):
    """Extracts coordinates from a sentence containing bracketed representations.

    Args:
        text (str): The input sentence containing coordinates in bracketed format.
        coords_type (str, optional): Type of coordinates to extract: 'bbox' (4 values), 'point' (2 values),
            or 'polygon' (3+ values). Defaults to 'bbox'.
        brackets_style (BracketsStyle, optional): The style of brackets used to enclose coordinates.
            Defaults to BracketsStyle.SQUARE.
        nested_style (NestedStyle, optional): The nesting style (single or double brackets).
            Defaults to NestedStyle.SINGLE.
        return_matches (bool, optional): If True, also returns the matched strings and their spans.
            Defaults to False.

    Returns:
        list: If return_matches is False, returns a list of extracted coordinates.
        tuple: If return_matches is True, returns a tuple (coords, matched_strings, spans).

    Example:
        >>> find_coordinates("Two apples {{1, 2, 3, 4}, {5,6,7,8}}", coords_type='bbox')
        [[[1, 2, 3, 4], [5, 6, 7, 8]]]
    """
    # Determine expected coord length based on type
    coord_lengths = {"bbox": 4, "point": 2, "polygon": lambda x: x >= 3}
    expected_len = coord_lengths.get(coords_type, 4)

    LB, RB = brackets_style.value["left"], brackets_style.value["right"]
    LB_p, RB_p = (
        (f"\{LB}", f"\{RB}")
        if brackets_style
        in [BracketsStyle.SQUARE, BracketsStyle.CURLY, BracketsStyle.PARENTHESES]
        else (LB, RB)
    )
    if nested_style == NestedStyle.DOUBLE:
        pattern = r"(%s\s*%s.*?%s\s*%s)" % (LB_p, LB_p, RB_p, RB_p)
    else:
        pattern = r"(%s\s*[\d\.,\s]+\s*%s)" % (LB_p, RB_p)

    res_coords, res_strs, res_spans = [], [], []
    for item in re.finditer(pattern, text):
        try:
            coords_lst = item.group(1).replace(LB, "[").replace(RB, "]")
            coords = ast.literal_eval(coords_lst)

            # Check based on coords_type
            if is_nested_list(coords):
                if callable(expected_len):
                    is_valid = all([expected_len(len(c)) for c in coords])
                else:
                    is_valid = all([len(c) == expected_len for c in coords])
                if is_valid:
                    parsed = [_coerce_coord_list(c) for c in coords]
                    if any(p is None for p in parsed):
                        continue
                    coords = parsed
                else:
                    continue
            elif is_single_list(coords):
                if callable(expected_len):
                    is_valid = expected_len(len(coords))
                else:
                    is_valid = len(coords) == expected_len
                if is_valid:
                    parsed = _coerce_coord_list(coords)
                    if parsed is None:
                        continue
                    coords = parsed
                else:
                    continue
            else:
                continue

            res_coords.append(coords)
            res_strs.append(item.group(1))
            res_spans.append(item.span())
        except:
            pass

    if return_matches:
        return res_coords, res_strs, res_spans
    else:
        return res_coords


def find_coordinates_all(text, coords_type="bbox", flat=True):
    found, ps_l, ps_r = [], [], []
    for nested_style in NestedStyle:  # Double first
        for brackets_style in BracketsStyle:
            for bbx, bbx_str, bbx_span in zip(
                *find_coordinates(
                    text,
                    coords_type,
                    brackets_style,
                    nested_style=nested_style,
                    return_matches=True,
                )
            ):
                ls = bisect.bisect_right(ps_l, bbx_span[0])
                if ls > 0 and bbx_span[1] <= ps_r[ls - 1]:
                    continue  # fall within existing span
                found.append((bbx, bbx_str, bbx_span))
                ps_l.insert(ls, bbx_span[0])
                ps_r.insert(ls, bbx_span[1])
    # ordering
    found_sort = []
    for bbx_str_span in sorted(found, key=lambda x: x[2][0]):
        found_sort.append(bbx_str_span[0])
    if len(found_sort) == 0:
        found_sort = [[]]  # default behavior
    if flat:
        found_sort = flat_boxes(found_sort)
    return found_sort


def draw_texts_on_frame(
    annotated_frame, points, labels, colors, renormalize=False, imgsize_wh=None
):
    # Draw labels with PIL (supports Chinese/UTF-8)
    pil_img = Image.fromarray(annotated_frame)
    draw = ImageDraw.Draw(pil_img)
    font_size = 18
    font = None
    for font_path in [
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/unifont/unifont.otf",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    ]:
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, font_size)
            break
    if font is None:
        font = ImageFont.load_default()
    # Re-apply renormalization for label positions
    for i, (point, lbl) in enumerate(zip(points, labels)):
        if renormalize:
            point = reverse_normalize_box(
                point, imgsize_wh[0], imgsize_wh[1], round_fn=lambda x: int(x)
            )
        text_pos = (point[0], max(point[1] - font_size - 4, 0))
        draw.text(text_pos, lbl, font=font, fill=colors[i])
    annotated_frame = np.array(pil_img)
    return annotated_frame


def visualize_boxes(
    img_path: str = None,
    img_bytes=None,
    boxes: list = [],
    labels: list = None,
    renormalize=False,
    save_path: str = None,
    return_b64=False,
    save_optimized=True,
    **kwargs,
):
    """
    Visualizes bounding boxes and labels on an image.

    Args:
        img_path (str, optional): Path to the input image file. Either `img_path` or `img_bytes` must be provided.
        img_bytes (bytes, optional): Image data in bytes. Used if `img_path` is not provided.
        boxes (list): List of bounding boxes, each box as [x1, y1, x2, y2].
        labels (list, optional): List of labels corresponding to each box. If None, empty labels are used.
        renormalize (bool, optional): If True, renormalizes box coordinates based on image size.
        save_path (str, optional): Path to save the annotated image. If None, image is not saved.
        return_b64 (bool, optional): If True, returns the annotated image as a base64-encoded string.
        save_optimized (bool, optional): If True, saves the image with JPEG optimization.
        **kwargs:
            colors (list, optional): List of colors for each box. Default is 'red' for all boxes.
            thickness (list, optional): List of thickness values for each box. Default is 2 for all boxes.

    Returns:
        np.ndarray or str: Annotated image as a numpy array (RGB) or base64 string if `return_b64` is True.

    Raises:
        AssertionError: If neither `img_path` nor `img_bytes` is provided.

    Example:
        >>> visualize_boxes(img_path="image.jpg", boxes=[[10, 20, 100, 200]], labels=["cat"], save_path="out.jpg")
    """
    assert (
        img_path is not None or img_bytes is not None
    ), "Either img_path or img_bytes must be provided."
    colors = kwargs.get("colors", ["red"] * len(boxes))
    thickness = kwargs.get("thickness", [2] * len(boxes))
    if img_path:
        img = cv2.imread(img_path)
    else:
        image_np = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert to RGB
    image_h, image_w, _ = img.shape

    labels = [""] * len(boxes) if labels is None else labels
    colors = [
        tuple(int(c * 255) for c in plt.matplotlib.colors.to_rgb(_)) for _ in colors
    ]

    annotated_frame = img.copy()
    for i, (box, lbl) in enumerate(zip(boxes, labels)):
        box = [int(_) for _ in box]
        box = (
            reverse_normalize_box(box, image_w, image_h, round_fn=lambda x: int(x))
            if renormalize
            else box
        )
        cv2.rectangle(
            annotated_frame, box[:2], box[2:], color=colors[i], thickness=thickness[i]
        )
        # cv2.putText does not support Chinese; use PIL instead
        # cv2.putText(annotated_frame, lbl, (box[0], box[1]-8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors[i],  1)

    # Draw labels with PIL (supports Chinese/UTF-8)
    annotated_frame = draw_texts_on_frame(
        annotated_frame,
        boxes,
        labels,
        colors,
        renormalize=renormalize,
        imgsize_wh=(image_w, image_h),
    )

    if save_path:
        pil_img = Image.fromarray(annotated_frame)
        if save_optimized:
            pil_img.save(save_path, format="JPEG", quality=85, optimize=True)
        else:
            pil_img.save(save_path)
    if return_b64:
        pil_img = Image.fromarray(annotated_frame)
        buffered = io.BytesIO()
        pil_img.save(buffered, format="JPEG")
        annotated_frame = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return annotated_frame


def visualize_points(
    img_path: str = None,
    img_bytes=None,
    points: list = [],
    labels: list = None,
    renormalize=False,
    diameters=None,
    save_path: str = None,
    return_b64=False,
    save_optimized=True,
    distinct_colors=False,
    colors=None,
):
    assert (
        img_path is not None or img_bytes is not None
    ), "Either img_path or img_bytes must be provided."
    if img_path:
        img = cv2.imread(img_path)
    else:
        image_np = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert to RGB
    image_h, image_w, _ = img.shape
    diameters = diameters or [max(3, min(img.shape) / 40)] * len(points)

    labels = [""] * len(points) if labels is None else labels
    colors = (
        [(255, 0, 0)] * len(points)
        if colors is None
        else [
            tuple(int(c * 255) for c in plt.matplotlib.colors.to_rgb(_)) for _ in colors
        ]
    )
    if distinct_colors:
        colors = get_distinct_colors_hsv(len(points), normalize=False)

    annotated_frame = img.copy()
    for i, (point, lbl) in enumerate(zip(points, labels)):
        point = [int(_) for _ in point]
        point = (
            reverse_normalize_box(point, image_w, image_h, round_fn=lambda x: int(x))
            if renormalize
            else point
        )
        # Draw points
        cv2.circle(
            annotated_frame,
            (point[0], point[1]),
            radius=diameters[i],
            color=colors[i],
            thickness=-1,
        )  # thickness=-1表示填充
    # Draw labels
    annotated_frame = draw_texts_on_frame(
        annotated_frame,
        points,
        labels,
        colors,
        renormalize=renormalize,
        imgsize_wh=(image_w, image_h),
    )

    if save_path:
        if save_optimized:
            Image.fromarray(annotated_frame).save(
                save_path, format="JPEG", quality=85, optimize=True
            )
        else:
            Image.fromarray(annotated_frame).save(save_path)
    if return_b64:
        pil_img = Image.fromarray(annotated_frame)
        buffered = io.BytesIO()
        pil_img.save(buffered, format="JPEG")
        annotated_frame = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return annotated_frame


def visualize_polys(
    img_path: str = None,
    img_bytes=None,
    polys: list = [],
    labels: list = None,
    is_closed=True,
    renormalize=False,
    save_path: str = None,
    return_b64=False,
    save_optimized=True,
):
    """polys: [[x1,y1], [x2,y2], ...], where the [x1,y2] is the top-left corner."""
    assert (
        img_path is not None or img_bytes is not None
    ), "Either img_path or img_bytes must be provided."
    if img_path:
        img = cv2.imread(img_path)
    else:
        image_np = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert to RGB
    image_h, image_w, _ = img.shape

    labels = [""] * len(polys) if labels is None else labels

    annotated_frame = img.copy()
    text_poss = []
    for poly, lbl in zip(polys, labels):
        poly = [[int(_) for _ in _p] for _p in poly]
        poly = (
            [
                reverse_normalize_box(_p, image_w, image_h, round_fn=lambda x: int(x))
                for _p in poly
            ]
            if renormalize
            else poly
        )
        # box = [int(box[0]*image_w), int(box[1]*image_h), int(box[2]*image_w), int(box[3]*image_h)]
        # Draw boxes
        cv2.polylines(
            annotated_frame,
            np.array([poly], dtype=np.int32),
            isClosed=is_closed,
            color=(144, 238, 144),
            thickness=2,
        )
        # Draw labels
        # cv2.putText(annotated_frame, label, coord, font, scale, (0, 0, 0),  1)
        # cv2.putText(annotated_frame, lbl, poly[0], cv2.FONT_HERSHEY_SIMPLEX, 0.5, (144,238,144),  1)
        text_poss.append(poly[0])
    # Draw label texts
    annotated_frame = draw_texts_on_frame(
        annotated_frame,
        text_poss,
        labels,
        [(144, 238, 144)] * len(polys),
        renormalize=renormalize,
        imgsize_wh=(image_w, image_h),
    )

    if save_path:
        if save_optimized:
            Image.fromarray(annotated_frame).save(
                save_path, format="JPEG", quality=85, optimize=True
            )
        else:
            Image.fromarray(annotated_frame).save(save_path)
    if return_b64:
        pil_img = Image.fromarray(annotated_frame)
        buffered = io.BytesIO()
        pil_img.save(buffered, format="JPEG")
        annotated_frame = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return annotated_frame


def parse_coordinates_from_response(
    response_str, coords_type="bbox", init_context_window=2000, max_context_window=-1
):
    """从模型回复文本中解析出有坐标值数组（coordinates组成的list，坐标值可能是bbox、point或polygon）。基本逻辑如下：
    初始，检查从后向前数第`init_context_window`个字符是否是bbox的一部分（即被截断），如果是，则向前拓展`init_context_window`，直至前一个字符不是bbox的一部分，或达到了`max_context_window`。
    然后，从选取的context_window中调用find_coordinates_all方法，找到所有坐标，flat之后返回list。
    """
    if not isinstance(response_str, str):
        return []
    context_window = init_context_window
    max_context_window = (
        len(response_str) if max_context_window < 0 else max_context_window
    )
    start_idx = max(0, len(response_str) - context_window)
    # 向前拓展context_window，直到前一个字符不是bbox的一部分
    bbox_chars = set("0123456789.,[]{}()<>' ")
    # 从枚举类BracketsStyle中获取所有括号字符
    for style in BracketsStyle:
        bbox_chars.update(style.value["left"])
        bbox_chars.update(style.value["right"])
    for style in BracketsStyle:
        bbox_chars.update(style.value["left"])
        bbox_chars.update(style.value["right"])
    while (
        start_idx > 0
        and response_str[start_idx - 1] in bbox_chars
        and context_window < max_context_window
    ):
        context_window += 1
        start_idx = max(0, len(response_str) - context_window)
    context_str = response_str[start_idx:]

    # 按不同的坐标类型解析
    res_coords = find_coordinates_all(context_str, coords_type=coords_type, flat=True)
    return res_coords
