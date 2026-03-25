import json
import re
from ast import literal_eval


def _to_number(v):
    """将数值/字符串安全转为 float。"""
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return float(s)
        except Exception:
            return None
    return None


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
            r"(\[\s*-*\d+\.*\d+\s*,\s*-*\d+\.*\d+\s*,\s*-*\d+\.*\d+\s*,\s*-*\d+\.*\d+\s*\])",
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

    # return strict_match, loose_match
    return loose_match


if __name__ == "__main__":

    # 测试parse_detection_from_response
    test_response_correct = """Here is the detected 2D bounding box:
[{"bbox_2d": [1.5, 2.0, 3.0, 1.0], "label": "car"}]
Note: the coordinates might be split across lines, but the function should still be able to parse them correctly. For example:
[{"bbox_2d": [1.5, 2.0, 3.0,
1.0, 2.0, 3.0], "label": "car"}]
And there might be some noise in the text as well."""
    test_response_incomplete = """Here is the detected 2D bounding box:
[{"bbox_2d": [1.5, 2.0, 3.0, 6.0], "label": "car"}]
Note: the coordinates might be split across lines, but the function should still be able to parse them correctly. For example:
[{"bbox_2d": [1.5, 2.0, 3.0, 1.0, 2.0, 3.0], "label": "car"}]
And there might be some noise in the text as well."""

    loose = parse_detection_from_response(
        test_response_incomplete, max_context_window=400
    )
    print("Loose match:", loose)
