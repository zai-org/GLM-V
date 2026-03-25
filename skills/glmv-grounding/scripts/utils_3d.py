"""
      v4_____________________v5
      /|                    /|
     / |                   / |
    /  |                  /  |
   /___|_________________/   |
v0|    |                 |v1 |
  |    |       y   z     |   |
  |    |       ↑ ↗       |   |
  |    |       · → x	   |   |
  |    |_________________|___|
  |   / v7               |   /v6
  |  /                   |  /
  | /                    | /
  |/_____________________|/
  v3                     v2
"""

import math, io, base64, json, ast, re
import numpy as np
import cv2
from PIL import Image
import matplotlib.pyplot as plt


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


def visualize_3d_boxes_glmv_simple(
    image_path,
    cam_params,
    bbox_3d_list,
    image_bytes=None,
    coord_format="xyzwhlpyr",
    save_path=None,
    save_optimized=False,
    return_b64=False,
    **kwargs,
):
    """Draw multiple 3D bounding boxes on the same image and return matplotlib figure.
    Args:
      format: 'xyzwhlpyr' or 'xyzXYZpyr', the former means (x,y,z,z_size,y_size,x_size,pitch,yaw,roll), and the later means (x,y,z,x_size,y_size,z_size,pitch,yaw,roll).
    """
    colors = kwargs.get("colors", ["red"] * len(bbox_3d_list))
    colors = [
        tuple(int(c * 255) for c in plt.matplotlib.colors.to_rgb(_)) for _ in colors
    ]
    thickness = kwargs.get("thickness", [2] * len(bbox_3d_list))

    def rotate_xyz(_point, _pitch, _yaw, _roll):
        # 1. rotate around x
        x0, y0, z0 = _point
        x1 = x0
        y1 = y0 * math.cos(_pitch) - z0 * math.sin(_pitch)
        z1 = y0 * math.sin(_pitch) + z0 * math.cos(_pitch)

        # 2. rotate around y
        x2 = x1 * math.cos(_yaw) + z1 * math.sin(_yaw)
        y2 = y1
        z2 = -x1 * math.sin(_yaw) + z1 * math.cos(_yaw)

        # 2. rotate around z
        x3 = x2 * math.cos(_roll) - y2 * math.sin(_roll)
        y3 = x2 * math.sin(_roll) + y2 * math.cos(_roll)
        z3 = z2
        return [x3, y3, z3]

    def convert_3dbbox(point, cam_params):
        """Convert 3D bounding box to 2D image coordinates"""
        x, y, z, x_size, y_size, z_size, pitch, yaw, roll = point
        hx, hy, hz = x_size / 2, y_size / 2, z_size / 2
        local_corners = [
            [hx, hy, hz],
            [hx, hy, -hz],
            [hx, -hy, hz],
            [hx, -hy, -hz],
            [-hx, hy, hz],
            [-hx, hy, -hz],
            [-hx, -hy, hz],
            [-hx, -hy, -hz],
        ]
        img_corners = []
        qwen_verts = []
        for corner in local_corners:
            # rotated = rotate_xyz(corner, np.deg2rad(pitch), np.deg2rad(yaw), np.deg2rad(roll))
            rotated = rotate_xyz(
                corner, pitch, yaw, roll
            )  # Qiji: different from Qwen3-vl who normalize radians by pi
            X, Y, Z = rotated[0] + x, rotated[1] + y, rotated[2] + z
            qwen_verts.append([X, Y, Z])
            if Z > 0:
                x_2d = cam_params["fx"] * (X / Z) + cam_params["cx"]
                y_2d = cam_params["fy"] * (Y / Z) + cam_params["cy"]
                img_corners.append([x_2d, y_2d])
            else:
                print(f"Z: {Z}, corner: {corner}")
        return img_corners

    # Read image
    if image_path:
        img = cv2.imread(image_path)
    else:
        image_np = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert to RGB
    # annotated_image = cv2.imread(image_path)
    annotated_image = img
    if annotated_image is None:
        print(f"Error reading image: {image_path}")
        return None

    edges = [
        [0, 1],
        [2, 3],
        [4, 5],
        [6, 7],
        [0, 2],
        [1, 3],
        [4, 6],
        [5, 7],
        [0, 4],
        [1, 5],
        [2, 6],
        [3, 7],
    ]

    # Draw 3D box for each bbox
    for i, bbox_data in enumerate(bbox_3d_list):
        # Extract bbox_3d from the dictionary
        if isinstance(bbox_data, dict) and "bbox_3d" in bbox_data:
            bbox_3d = bbox_data["bbox_3d"]
        else:
            bbox_3d = bbox_data

        # Convert angles multiplied by 180 to degrees
        bbox_3d = list(bbox_3d)  # Convert to list for modification
        # bbox_3d[-3:] = [_x * 180 for _x in bbox_3d[-3:]]  # Qiji: different from Qwen3-vl who normalize radians by pi

        if coord_format == "xyzwhlpyr":
            bbox_3d = [
                *bbox_3d[:3],
                *bbox_3d[3:6][::-1],
                *bbox_3d[6:],
            ]  # convert to 'xyzwhlpyr'
        elif coord_format == "xyzXYZpyr":
            pass

        bbox_2d = convert_3dbbox(bbox_3d, cam_params)
        # print(f"bbox_2d: {bbox_2d}")

        if len(bbox_2d) >= 8:
            # Generate random color for each box
            # box_color = [random.randint(0, 255) for _ in range(3)]
            box_color = colors[i] if colors else [255, 0, 0]  # red
            for start, end in edges:
                try:
                    pt1 = tuple([int(_pt) for _pt in bbox_2d[start]])
                    pt2 = tuple([int(_pt) for _pt in bbox_2d[end]])
                    cv2.line(
                        annotated_image,
                        pt1,
                        pt2,
                        box_color,
                        thickness[i] if thickness else 2,
                    )
                except:
                    continue
            if "label" in bbox_data:
                cv2.putText(
                    annotated_image,
                    bbox_data["label"],
                    [round(_) for _ in bbox_2d[6]],
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    box_color,
                    1,
                )
    if save_path:
        if save_optimized:
            Image.fromarray(annotated_image).save(
                save_path, format="JPEG", quality=85, optimize=True
            )
        else:
            Image.fromarray(annotated_image).save(save_path)

    # Convert BGR to RGB for matplotlib
    # annotated_image_rgb = cv2.cvtColor(annotated_image, cv2.COLOR_BGR2RGB)

    # Create matplotlib figure
    # fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    # ax.imshow(annotated_image_rgb)
    # ax.axis('off')
    if return_b64:
        pil_img = Image.fromarray(annotated_image)
        buffered = io.BytesIO()
        pil_img.save(buffered, format="JPEG")
        annotated_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return annotated_image


def parse_3d_boxes_from_response(response_str, max_context_window=-1):
    """从模型回复文本中解析出3D bounding boxes: `[{\"bbox_3d\":[x_center, y_center, z_center, x_size, y_size, z_size, roll, pitch, yaw],\"label\":\"category\"}, ...]`，结果是一个由JSON对象组成的list，每个JSON对象包含一个类别标签和一个由8个坐标数值组成的3D坐标框。基本逻辑如下：
    - 解析出两个结果，一个是直接找到左、右括号字符，然后直接严格解析找到的字符串，作为strict_match结果；
    - 另一个是按括号匹配算法从后向前收集的结果，作为loose_match结果，匹配算法逻辑如下：
      + 从最后一个字符开始向前做栈式括号匹配算法，找到完整的[{"bbox_3d", [...]}, {}, ...]字符串。即从后向前查找，每逢右括号就入栈，每逢左括号就出栈，当匹配完整的JSON时（即{"bbox_3d": [...]})记录一个3D坐标框的字符串，直到找到最后一个完整的JSON字符串为止。这个过程可以确保即使坐标被截断了（如被分成两行输出），也能正确地找到完整的坐标字符串。当栈空或达到`max_context_window`时停止。

    最终，返回strict_match和loose_match。
    """

    def _normalize_items(obj):
        """将解析结果统一成 [{'bbox_3d': [...], 'label': ...}, ...]。"""
        if isinstance(obj, dict):
            obj = [obj]
        if not isinstance(obj, list):
            return []

        out = []
        for item in obj:
            if not isinstance(item, dict):
                continue
            if "bbox_3d" not in item:
                continue
            bbox = item.get("bbox_3d")
            if not isinstance(bbox, (list, tuple)):
                continue

            nums = []
            ok = True
            for v in bbox:
                n = _to_number(v)
                if n is None:
                    ok = False
                    break
                nums.append(n)
            if not ok or len(nums) < 8:  # 兼容8/9维
                continue

            rec = {"bbox_3d": nums}
            if "label" in item and item["label"] is not None:
                rec["label"] = str(item["label"])
            out.append(rec)
        return out

    def _parse_text_block(text):
        """严格 JSON + 宽松 literal_eval。"""
        if not isinstance(text, str):
            return []
        s = text.strip()
        if not s:
            return []

        for loader in (json.loads, ast.literal_eval):
            try:
                obj = loader(s)
                norm = _normalize_items(obj)
                if norm:
                    return norm
            except Exception:
                pass
        return []

    # 防御式处理输入
    if not isinstance(response_str, str) or not response_str.strip():
        return [], []

    text = response_str
    strict_match = []
    loose_match = []

    # ---------- strict_match ----------
    # 1) 先按正则匹配形如 [ {...}, {...}, ... ] 的候选片段
    #    这里要求对象中出现 bbox_3d，并优先选择可解析且数量最多的结果
    pattern = re.compile(
        r'\[\s*\{[\s\S]*?"bbox_3d"\s*:\s*\[[^\]]*\][\s\S]*?\}'
        r'(?:\s*,\s*\{[\s\S]*?"bbox_3d"\s*:\s*\[[^\]]*\][\s\S]*?\})*\s*\]',
        re.DOTALL,
    )

    best = []
    for m in pattern.finditer(text):
        seg = m.group(0)
        parsed = _parse_text_block(seg)
        if parsed and len(parsed) > len(best):
            best = parsed
    strict_match = best

    # ---------- loose_match ----------
    # 从后向前，栈式匹配，优先寻找“最右侧完整数组”
    n = len(text)
    window = (
        n
        if (max_context_window is None or max_context_window < 0)
        else min(n, int(max_context_window))
    )
    start_limit = max(0, n - window)

    stack = []  # [(char, idx)]
    pairs = {"[": "]", "{": "}"}
    started = False

    for i in range(n - 1, start_limit - 1, -1):
        ch = text[i]

        if ch in "]}":
            stack.append((ch, i))
            started = True
            continue

        if ch in "[{":
            if not stack:
                continue
            top_ch, top_idx = stack[-1]
            if pairs[ch] != top_ch:
                # 括号类型不一致，丢弃当前top继续
                stack.pop()
                continue

            stack.pop()  # 成功匹配 ch ... top_idx

            # 优先尝试数组片段
            if ch == "[":
                seg = text[i : top_idx + 1]
                if "bbox_3d" in seg:
                    parsed = _parse_text_block(seg)
                    if parsed:
                        loose_match = parsed
                        break

            # 如果已经进入匹配过程且栈清空，说明一个完整后缀段结束，可停止
            if started and not stack:
                break

    # 若数组未找到，退化为“从后向前抽取单个对象”
    if not loose_match:
        stack = []
        objs = []
        for i in range(n - 1, start_limit - 1, -1):
            ch = text[i]
            if ch == "}":
                stack.append((ch, i))
            elif ch == "{":
                if not stack:
                    continue
                top_ch, top_idx = stack[-1]
                if top_ch != "}":
                    stack.pop()
                    continue
                stack.pop()
                seg = text[i : top_idx + 1]
                if "bbox_3d" in seg:
                    one = _parse_text_block(seg)
                    if one:
                        # _parse_text_block(dict) 会返回长度1列表
                        objs.extend(one)
                if not stack and objs:
                    break
        if objs:
            loose_match = list(reversed(objs))

    return strict_match, loose_match


if __name__ == "__main__":

    # 测试parse_3d_boxes_from_response
    test_response_correct = """Here is the detected 3D bounding box:
[{"bbox_3d": [1.5, 2.0, 3.0, 1.0, 2.0, 3.0, 10, 20, 30], "label": "car"}]
Note: the coordinates might be split across lines, but the function should still be able to parse them correctly. For example:
[{"bbox_3d": [1.5, 2.0, 3.0,
1.0, 2.0, 3.0, 10, 20, 30], "label": "car"}]
And there might be some noise in the text as well."""
    test_response_incomplete = """Here is the detected 3D bounding box:
[{"bbox_3d": [1.5, 2.0, 3.0, 1.0, 2.0, 3.0, 10, 20, 30]}]
Note: the coordinates might be split across lines, but the function should still be able to parse them correctly. For example:
[{"bbox_3d": [1.5, 2.0, 3.0,
1.0, 2.0, 3.0], "label": "car"}]
And there might be some noise in the text as well."""

    strict, loose = parse_3d_boxes_from_response(test_response_incomplete)
    print("Strict match:", strict)
    print("Loose match:", loose)
