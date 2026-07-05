"""缠论核心算法实现"""
from typing import List
from app.models.stock_model import KlineData
from app.models.chan_model import ClassicChanKline, Fractal, Pen, Segment, ZhongShu, DAY
from app.core.chan_helpers import (
    is_kline_contained,
    _can_form_pen,
    _can_form_pen_v1,
    generate_pens,
    validate_pens,
    pen_high,
    pen_low,
    validate_segments,
    validate_segments_v1,
    _build_char_sequence,
    _process_char_sequence_inclusion,
    _has_gap,
    _identify_char_fractals,
    CharElement,
    _find_overlaps_break,
)


def process_inclusion(klines: List[KlineData]) -> List[ClassicChanKline]:
    """
    处理K线包含关系
    在上升趋势中，取两根K线的最高价为新K线最高价，两根K线的较高的最低价为新K线最低价
    在下降趋势中，取两根K线的最低价为新K线最低价，两根K线的较低的最高价为新K线最高价
    """
    if len(klines) < 2:
        return klines

    first = ClassicChanKline(
        index=0,
        start=0,
        end=0,
        high=klines[0].high,
        low=klines[0].low
    )
    processed = [first]
    direction = 'up'  # 'up' or 'down', default 'up'
    count = 0

    for i in range(1, len(klines)):
        current = ClassicChanKline(
            index=i,
            start=i,
            end=i,
            high=klines[i].high,
            low=klines[i].low
        )
        prev = processed[-1]

        # 判断是否存在包含关系
        if not is_kline_contained(current, prev):
            # 无包含关系，确定方向
            if current.high > prev.high:
                direction = 'up'
            elif current.high < prev.high:
                direction = 'down'
            count += 1
            processed.append(ClassicChanKline(
                index=count,
                start=current.start,
                end=current.end,
                high=current.high,
                low=current.low
            ))
        else:
            # 有包含关系，根据方向处理
            if direction == 'up':
                # 上升趋势：取高中高，低中高
                new_kline = ClassicChanKline(
                    index=count,
                    start=prev.start,
                    end=current.end,
                    high=max(current.high, prev.high),
                    low=max(current.low, prev.low)
                )
            elif direction == 'down':
                # 下降趋势：取低中低，高中低
                new_kline = ClassicChanKline(
                    index=count,
                    start=prev.start,
                    end=current.end,
                    high=min(current.high, prev.high),
                    low=min(current.low, prev.low)
                )
            else:
                # 方向未确定，默认合并
                print(f"error: direction not determined: {direction}")
                new_kline = ClassicChanKline(
                    index=count,
                    start=prev.start,
                    end=current.end,
                    high=current.high,
                    low=current.low
                )

            processed[-1] = new_kline

    return processed


def identify_fractals(klines: List[ClassicChanKline], raw_klines: List[KlineData]) -> List[Fractal]:
    """
    识别顶底分型
    顶分型：第二根K线的高点是三根中最高的，且第二根K线的低点也是三根中最高的
    底分型：第二根K线的低点是三根中最低的，且第二根K线的高点也是三根中最低的
    """
    fractals = []

    for i in range(1, len(klines) - 1):
        prev_k = klines[i - 1]
        curr_k = klines[i]
        next_k = klines[i + 1]

        # 顶分型判断
        if (curr_k.high > prev_k.high and curr_k.high > next_k.high and
            curr_k.low > prev_k.low and curr_k.low > next_k.low):
            k_index = curr_k.end
            for k in range(curr_k.end, curr_k.start - 1, -1):
                if raw_klines[k].high == curr_k.high:
                    k_index = k
                    break
                if k == curr_k.start:
                    print("error: no match date found: ", curr_k)
            fractals.append(Fractal(
                index=curr_k.index,
                k_index=k_index,
                date=raw_klines[k_index].date,
                type="top"
            ))

        # 底分型判断
        elif (curr_k.low < prev_k.low and curr_k.low < next_k.low and
              curr_k.high < prev_k.high and curr_k.high < next_k.high):
            k_index = curr_k.end
            for k in range(curr_k.end, curr_k.start - 1, -1):
                if raw_klines[k].low == curr_k.low:
                    k_index = k
                    break
                if k == curr_k.start:
                    print("error: no match date found: ", curr_k)
            fractals.append(Fractal(
                index=curr_k.index,
                k_index=k_index,
                date=raw_klines[k_index].date,
                type="bottom"
            ))

    return fractals


def generate_new_pens(fractals: List[Fractal], klines: List[ClassicChanKline]) -> List[Pen]:
    """
    生成笔（三步法）

    第一步：从左到右遍历分型列表，若相邻两个分型类型不同，判断能否成笔
            （缠论K线索引差>=3 且 实际K线间距>=3条）。不能成笔则删除后者。
    第二步：对连续同类型分型，顶分型只保留最高的，底分型只保留最低的，
            保证顶底分型交替出现。
    第三步：根据处理后的分型列表依次连接构成笔。
    """
    if len(fractals) < 2:
        return []

    # ---- 第一步：删除不能成笔的相邻分型 ----
    filtered: List[Fractal] = [fractals[0]]
    for i in range(1, len(fractals)):
        prev_f = filtered[-1]
        curr_f = fractals[i]
        if prev_f.type != curr_f.type:
            # 类型不同，检查能否成笔
            if _can_form_pen(prev_f, curr_f, klines):
                filtered.append(curr_f)
            # 不能成笔：删除当前分型（不加入 filtered）
        else:
            # 类型相同，暂时保留，第二步再处理
            filtered.append(curr_f)

    # ---- 第二步：合并连续同类型分型 ----
    merged: List[Fractal] = [filtered[0]]
    for i in range(1, len(filtered)):
        curr_f = filtered[i]
        last = merged[-1]
        if curr_f.type == last.type:
            # 连续同类型：顶分型保留最高的，底分型保留最低的
            if curr_f.type == "top":
                if klines[curr_f.index].high > klines[last.index].high:
                    merged[-1] = curr_f
            else:  # bottom
                if klines[curr_f.index].low < klines[last.index].low:
                    merged[-1] = curr_f
        else:
            merged.append(curr_f)

    # ---- 第三步：依次连接成笔 ----
    pens: List[Pen] = []
    for i in range(0, len(merged) - 1):
        f1 = merged[i]
        f2 = merged[i + 1]
        if f1.type == f2.type:
            print(f"error: 相邻分型类型相同，无法成笔: index={f1.index}({f1.type}) -> index={f2.index}({f2.type}), date={f1.date} -> {f2.date}")
            continue
        direction = "up" if f1.type == "bottom" else "down"
        pens.append(Pen(
            start_index=f1.index,
            end_index=f2.index,
            start_date=f1.date,
            end_date=f2.date,
            direction=direction,
        ))

    return pens


def generate_new_pens_v1(fractals: List[Fractal], klines: List[ClassicChanKline]) -> List[Pen]:
    """
    [v1备份] 生成新笔 (§2.1–§2.4 of pen.md)

    算法：
    - 顺序遍历分型列表，维护"当前笔起始分型"。
    - 遇到反向分型时，尝试成笔（类型交替 + 间距 + 方向 + 可选缺口）。
    - 若成笔，发出该笔，反向分型成为新的起始分型候选。
    - 若遇到同方向更极端的分型（更高的顶/更低的底），替换当前起始分型（§2.4 笔的延伸）。
    - 其余情况跳过。

    缺口成笔：间距不足时，若缺口K线（分型右侧K线）完全高于/低于前一笔的最高/最低点，也可成笔。
    """
    if len(fractals) < 2:
        return []

    pens: List[Pen] = []

    # 阶段1：找到第一笔作为引导（第一笔没有前一笔，不支持缺口成笔）
    start_idx = 0
    found_first = False
    for i in range(1, len(fractals)):
        if _can_form_pen_v1(fractals[start_idx], fractals[i], klines, prev_pen=None):
            direction = "up" if fractals[start_idx].type == "bottom" else "down"
            pens.append(Pen(
                start_index=fractals[start_idx].index,
                end_index=fractals[i].index,
                start_date=fractals[start_idx].date,
                end_date=fractals[i].date,
                direction=direction,
            ))
            start_idx = i
            found_first = True
            break
        # 同类型 — 保留更极端的分型（更高的顶或更低的底）
        if fractals[i].type == fractals[start_idx].type:
            if fractals[i].type == "top":
                if klines[fractals[i].index].high > klines[fractals[start_idx].index].high:
                    start_idx = i
            else:
                if klines[fractals[i].index].low < klines[fractals[start_idx].index].low:
                    start_idx = i

    if not found_first:
        return []

    # 阶段2：逐个处理剩余分型
    current_start = start_idx
    for i in range(start_idx + 1, len(fractals)):
        candidate = fractals[i]
        start_f = fractals[current_start]

        if candidate.type != start_f.type:
            # 反向分型 — 尝试成笔，传入前一笔用于缺口判断
            prev_pen = pens[-1] if pens else None
            if _can_form_pen_v1(start_f, candidate, klines, prev_pen=prev_pen):
                direction = "up" if start_f.type == "bottom" else "down"
                pens.append(Pen(
                    start_index=start_f.index,
                    end_index=candidate.index,
                    start_date=start_f.date,
                    end_date=candidate.date,
                    direction=direction,
                ))
                current_start = i
            # else: 间距不足/方向不对/无缺口 — 跳过
        else:
            # 同类型 — §2.4 笔的延伸：用更极端的分型替换当前起始分型
            replaced = False
            if candidate.type == "top":
                if klines[candidate.index].high > klines[start_f.index].high:
                    replaced = True
            else:  # bottom
                if klines[candidate.index].low < klines[start_f.index].low:
                    replaced = True

            if replaced:
                current_start = i
                # 同步延伸最近一笔的终点到更极端的分型
                if pens:
                    pens[-1].end_index = candidate.index
                    pens[-1].end_date = candidate.date

    return pens


def generate_segments_v1(pens: List[Pen], klines: List[ClassicChanKline]) -> List[Segment]:
    """
    [v1备份] 生成段（严格满足缠论定义）

    规则：
    - 每段至少3根笔，且笔数为奇数
    - 向上段以向上笔起始并以向上笔结束
    - 向下段以向下笔起始并以向下笔结束
    - 相邻段方向交替

    断段条件：
    - 向上段中，向下笔比前一同向向下笔更低（high和low都更低）→ 向上段结束
    - 向下段中，向上笔比前一同向向上笔更高（high和low都更高）→ 向下段结束
    """
    if len(pens) < 3:
        return []

    MIN_SEGMENT_PENS = 3

    segments: List[Segment] = []
    seg_start = 0
    seg_direction = pens[0].direction

    def _close_segment(end_idx: int) -> None:
        """将当前段收尾并加入列表，方向取自 seg_direction（即起始笔方向）"""
        top = max(pen_high(pens[i], klines) for i in range(seg_start, end_idx + 1))
        bottom = min(pen_low(pens[i], klines) for i in range(seg_start, end_idx + 1))
        segments.append(Segment(
            start_index=seg_start,
            end_index=end_idx,
            top=top,
            bottom=bottom,
            direction=seg_direction,
        ))

    for i in range(1, len(pens)):
        pen = pens[i]

        if seg_direction == "up" and pen.direction == "down":
            # 向上段中遇到向下笔：与同方向的前一根向下笔比较
            prev_same_dir_idx = -1
            for j in range(i - 1, seg_start - 1, -1):
                if pens[j].direction == "down":
                    prev_same_dir_idx = j
                    break
            if prev_same_dir_idx >= 0:
                prev_same_dir = pens[prev_same_dir_idx]
                if pen_high(pen, klines) < pen_high(prev_same_dir, klines) and \
                   pen_low(pen, klines) < pen_low(prev_same_dir, klines):
                    seg_end_idx = prev_same_dir_idx - 1
                    pen_count = seg_end_idx - seg_start + 1
                    if pen_count >= MIN_SEGMENT_PENS and pen_count % 2 == 1:
                        _close_segment(seg_end_idx)
                        seg_start = prev_same_dir_idx
                        seg_direction = "down"
                        continue

        elif seg_direction == "down" and pen.direction == "up":
            # 向下段中遇到向上笔：与同方向的前一根向上笔比较
            prev_same_dir_idx = -1
            for j in range(i - 1, seg_start - 1, -1):
                if pens[j].direction == "up":
                    prev_same_dir_idx = j
                    break
            if prev_same_dir_idx >= 0:
                prev_same_dir = pens[prev_same_dir_idx]
                if pen_high(pen, klines) > pen_high(prev_same_dir, klines) and \
                   pen_low(pen, klines) > pen_low(prev_same_dir, klines):
                    seg_end_idx = prev_same_dir_idx - 1
                    pen_count = seg_end_idx - seg_start + 1
                    if pen_count >= MIN_SEGMENT_PENS and pen_count % 2 == 1:
                        _close_segment(seg_end_idx)
                        seg_start = prev_same_dir_idx
                        seg_direction = "up"
                        continue

    # 收尾最后一段
    remaining_pens = len(pens) - seg_start
    if remaining_pens >= MIN_SEGMENT_PENS:
        if remaining_pens % 2 == 1:
            _close_segment(len(pens) - 1)
        else:
            _close_segment(len(pens) - 2)
    elif remaining_pens > 0 and segments:
        segments[-1].end_index = len(pens) - 1
        segments[-1].top = max(
            segments[-1].top,
            max(pen_high(pens[i], klines) for i in range(seg_start, len(pens)))
        )
        segments[-1].bottom = min(
            segments[-1].bottom,
            min(pen_low(pens[i], klines) for i in range(seg_start, len(pens)))
        )

    segments = validate_segments_v1(segments, pens, klines, MIN_SEGMENT_PENS)

    return segments


def generate_segments(pens: List[Pen], klines: List[ClassicChanKline]) -> List[Segment]:
    """
    生成段（v2 — 特征序列法）

    算法步骤：
    1. 构建当前段的特征序列（与段方向相反的笔）
    2. 对特征序列做包含处理 → 标准特征序列
    3. 识别分型（向上段找顶分型，向下段找底分型）
    4. 找到分型后：
       - 第一种情况（无缺口）：段在分型极值点结束
       - 第二种情况（有缺口）：构造反向验证序列，出现分型则段结束
    5. 段结束后新段开始，方向反转

    规则：
    - 每段至少3根笔，且笔数为奇数
    - 向上段以向上笔起始并以向上笔结束
    - 向下段以向下笔起始并以向下笔结束
    - 相邻段方向交替
    """
    if len(pens) < 3:
        return []

    MIN_SEGMENT_PENS = 3
    segments: List[Segment] = []
    seg_start = 0
    seg_direction = pens[0].direction

    def _close_segment(end_idx: int) -> None:
        """将当前段收尾并加入列表"""
        top = max(pen_high(pens[i], klines) for i in range(seg_start, end_idx + 1))
        bottom = min(pen_low(pens[i], klines) for i in range(seg_start, end_idx + 1))
        segments.append(Segment(
            start_index=seg_start,
            end_index=end_idx,
            top=top,
            bottom=bottom,
            direction=seg_direction,
        ))

    # 逐段处理：从 seg_start 开始扫描，直到找到段结束点
    while seg_start < len(pens):
        seg_direction = pens[seg_start].direction

        # 至少需要3根笔才能成段
        if len(pens) - seg_start < MIN_SEGMENT_PENS:
            break

        # ---- 步骤1：检查同向笔重合约束 ----
        # 向上段中 Si 与 Si+1 必须有重合区间，否则段终结于 Si
        # 向下段中 Xi 与 Xi+1 必须有重合区间，否则段终结于 Xi
        overlap_break_idx = _find_overlaps_break(pens, klines, seg_start, seg_direction)

        # ---- 步骤2-4：特征序列法寻找段结束点 ----
        char_end_idx = _find_segment_end(pens, klines, seg_start, seg_direction)

        # 取两者中更早的断点
        if overlap_break_idx is not None and char_end_idx is not None:
            seg_end_idx = min(overlap_break_idx, char_end_idx)
        elif overlap_break_idx is not None:
            seg_end_idx = overlap_break_idx
        elif char_end_idx is not None:
            seg_end_idx = char_end_idx
        else:
            # 未找到段结束点，剩余笔全部作为尾部
            break

        # ---- 步骤4：关闭当前段 ----
        _close_segment(seg_end_idx)
        seg_start = seg_end_idx + 1

    # ---- 步骤7：尾部段处理 ----
    remaining_pens = len(pens) - seg_start
    if remaining_pens >= MIN_SEGMENT_PENS:
        if remaining_pens % 2 == 1:
            _close_segment(len(pens) - 1)
        else:
            # 偶数笔截断1笔使其奇数
            _close_segment(len(pens) - 2)
    elif remaining_pens > 0 and segments:
        # 不足3笔的尾部合并到前一段
        segments[-1].end_index = len(pens) - 1
        segments[-1].top = max(
            segments[-1].top,
            max(pen_high(pens[i], klines) for i in range(seg_start, len(pens)))
        )
        segments[-1].bottom = min(
            segments[-1].bottom,
            min(pen_low(pens[i], klines) for i in range(seg_start, len(pens)))
        )

    # ---- 步骤8：后处理校验 ----
    segments = validate_segments(segments, pens, klines, MIN_SEGMENT_PENS)

    return segments


def _find_extremum_pen_idx(elem: "CharElement", extremum_type: str,
                           pens: List[Pen], klines: List[ClassicChanKline]) -> int:
    """
    在特征序列元素的 pen_indices 中找到极值笔的索引。

    经包含处理后，一个 CharElement 可能由多个原始笔合并而来，
    需要在这些笔中找到实际产生极值的笔。

    Args:
        elem: 特征序列元素
        extremum_type: "high" 找最高点对应的笔，"low" 找最低点对应的笔
        pens: 笔列表
        klines: 缠论K线列表

    Returns:
        极值笔在 pens 列表中的索引
    """
    if len(elem.pen_indices) == 1:
        return elem.pen_indices[0]

    best_idx = elem.pen_indices[0]
    if extremum_type == "high":
        best_val = pen_high(pens[best_idx], klines)
        for idx in elem.pen_indices[1:]:
            val = pen_high(pens[idx], klines)
            if val > best_val:
                best_val = val
                best_idx = idx
    else:  # "low"
        best_val = pen_low(pens[best_idx], klines)
        for idx in elem.pen_indices[1:]:
            val = pen_low(pens[idx], klines)
            if val < best_val:
                best_val = val
                best_idx = idx

    return best_idx


def _find_segment_end(pens: List[Pen], klines: List[ClassicChanKline],
                      seg_start: int, seg_direction: str) -> int | None:
    """
    从 seg_start 开始，用特征序列法寻找当前段的结束笔索引。

    向上段：在特征序列（向下笔）中找顶分型，在第二元素的极值笔（最高点）处划分
    向下段：在特征序列（向上笔）中找底分型，在第二元素的极值笔（最低点）处划分

    包含处理后，标准特征序列的一个元素可能由多个原始笔合并而来，
    因此需要在第二元素的 pen_indices 中找到极值笔，而不是直接取 pen_index。

    找到分型后：
    - 第一种情况（第一元素和第二元素之间无缺口）：段在极值笔处结束
    - 第二种情况（有缺口）：需要构造反向验证序列，出现分型才确认结束

    Returns:
        段结束笔索引（包含在该段内），若未找到返回 None
    """
    # 构建特征序列
    # 主特征序列开启 include_prev_pen：当前段非首段时，将前段末笔（反向笔）
    # 纳入特征序列首部，避免段首几笔因包含合并丢失分型而误延展段终点。
    char_seq = _build_char_sequence(pens, seg_start, seg_direction, klines,
                                    include_prev_pen=True)
    if len(char_seq) < 3:
        # 特征序列不足3个元素，无法形成分型
        return None

    # 包含处理 → 标准特征序列（传入段方向作为先验趋势方向）
    std_seq = _process_char_sequence_inclusion(char_seq, seg_direction)
    if len(std_seq) < 3:
        return None

    # 识别分型
    target_fractal_type = "top" if seg_direction == "up" else "bottom"
    char_fractals = _identify_char_fractals(std_seq)

    for fractal in char_fractals:
        if fractal.type != target_fractal_type:
            continue

        # 在第二元素的 pen_indices 中找到极值笔
        # 向上段顶分型 → 找最高点对应的笔
        # 向下段底分型 → 找最低点对应的笔
        extremum_type = "high" if seg_direction == "up" else "low"
        extremum_pen_idx = _find_extremum_pen_idx(fractal.second_elem, extremum_type, pens, klines)

        # 判断第一元素和第二元素之间是否有缺口
        has_gap = _has_gap(fractal.first_elem, fractal.second_elem)

        if not has_gap:
            # ---- 第一种情况：无缺口，段在极值笔处结束 ----
            # 段结束笔索引 = 极值笔的前一笔（因为段以同向笔结束）
            end_idx = extremum_pen_idx - 1
            pen_count = end_idx - seg_start + 1
            if pen_count >= 3 and pen_count % 2 == 1:
                return end_idx
        else:
            # ---- 第二种情况：有缺口，需要验证 ----
            # 从极值笔开始，构造反向段的特征序列
            reverse_dir = "down" if seg_direction == "up" else "up"
            verify_char_seq = _build_char_sequence(pens, extremum_pen_idx, reverse_dir, klines)
            if len(verify_char_seq) < 3:
                # 验证序列不足以形成分型，当前段继续
                continue

            verify_std_seq = _process_char_sequence_inclusion(verify_char_seq, reverse_dir)
            if len(verify_std_seq) < 3:
                continue

            verify_fractals = _identify_char_fractals(verify_std_seq)
            # 反向段只需出现任意分型即可确认（不区分第一/二种情况）
            if verify_fractals:
                end_idx = extremum_pen_idx - 1
                pen_count = end_idx - seg_start + 1
                if pen_count >= 3 and pen_count % 2 == 1:
                    return end_idx
            # 验证序列中未出现分型，当前段继续，尝试下一个分型

    return None


def identify_zhongshus(pens: List[Pen], klines: List[ClassicChanKline], level = DAY) -> List[ZhongShu]:
    """
    识别中枢
    简化实现：至少三笔重叠的区域构成中枢
    """
    if len(pens) < 3:
        return []

    zhongshus = []

    for i in range(len(pens) - 2):
        pen1, pen2, pen3 = pens[i], pens[i + 1], pens[i + 2]

        high1 = pen_high(pen1, klines)
        low1 = pen_low(pen1, klines)
        high2 = pen_high(pen2, klines)
        low2 = pen_low(pen2, klines)
        high3 = pen_high(pen3, klines)
        low3 = pen_low(pen3, klines)

        # 检查是否有重叠
        overlap_high = min(high1, high2, high3)
        overlap_low = max(low1, low2, low3)

        if overlap_high > overlap_low:
            zhongshus.append(ZhongShu(
                start_index=pen1.start_index,
                end_index=pen3.end_index,
                high=overlap_high,
                low=overlap_low,
                level=1
            ))

    return zhongshus


def calculate_chan_data(klines: List[KlineData], level = DAY) -> dict:
    """
    计算缠论数据

    Args:
        klines: K线数据列表

    Returns:
        包含分型、笔、段、中枢的字典
    """
    if not klines:
        return {
            "fractals": [],
            "pens": [],
            "segments": [],
            "zhongshus": []
        }

    # 1. 处理包含关系（始终输出 List[ClassicChanKline]）
    processed_klines: List[ClassicChanKline] = process_inclusion(klines)
    print(f"processed_klines: \n")
    for kline in processed_klines:
        print(kline)
    # 2. 识别分型
    fractals = identify_fractals(processed_klines, klines)

    # 3. 生成笔并校验（消除平行笔）
    pens = generate_new_pens(fractals, processed_klines)
    pens = validate_pens(pens, processed_klines)

    # 4. 生成段
    segments = generate_segments(pens, processed_klines)

    # 5. 识别中枢
    zhongshus = identify_zhongshus(pens, processed_klines, level)

    return {
        "chan_klines": processed_klines,
        "fractals": fractals,
        "pens": pens,
        "segments": segments,
        "zhongshus": zhongshus
    }
