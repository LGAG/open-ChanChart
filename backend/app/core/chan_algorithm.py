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


def generate_segments(pens: List[Pen], klines: List[ClassicChanKline]) -> List[Segment]:
    """
    生成段

    简化规则：
    - 在向上段中，如果某根向下笔的最高点和最低点都低于前一根向下笔的最高点和最低点，
      则向上段结束。前一根向下笔成为新向下段的第一根笔（破坏笔为第三根笔）。
    - 在向下段中，如果某根向上笔的最高点和最低点都高于前一根向上笔的最高点和最低点，
      则向下段结束。前一根向上笔成为新向上段的第一根笔（破坏笔为第三根笔）。

    约束：
    - 每段至少包含3根笔
    - 不允许平行段（相邻段方向必须交替）
    - 向上段终点高于起点，向下段终点低于起点
    """
    if len(pens) < 3:
        return []

    MIN_SEGMENT_PENS = 3

    segments: List[Segment] = []
    seg_start = 0
    seg_direction = pens[0].direction

    def _close_segment(end_idx: int, direction: str) -> None:
        """将当前段收尾并加入列表"""
        top = max(pen_high(pens[i], klines) for i in range(seg_start, end_idx + 1))
        bottom = min(pen_low(pens[i], klines) for i in range(seg_start, end_idx + 1))
        segments.append(Segment(
            start_index=seg_start,
            end_index=end_idx,
            top=top,
            bottom=bottom,
            direction=direction,
        ))

    for i in range(1, len(pens)):
        pen = pens[i]
        pen_count = i - seg_start  # 当前段内笔数（不含当前笔 i）

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
                    # 向下笔更低 → 向上段结束
                    # 破坏笔(pen i)是新向下段的第三笔，前一同向笔(prev_same_dir)是第一笔
                    # 所以新向下段从 prev_same_dir_idx 开始，向上段在 prev_same_dir_idx - 1 结束
                    seg_end_idx = prev_same_dir_idx - 1
                    # 但必须保证向上段至少有 MIN_SEGMENT_PENS 根笔
                    up_seg_pen_count = seg_end_idx - seg_start + 1
                    if up_seg_pen_count >= MIN_SEGMENT_PENS:
                        _close_segment(seg_end_idx, "up")
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
                    # 向上笔更高 → 向下段结束
                    # 破坏笔(pen i)是新向上段的第三笔，前一同向笔(prev_same_dir)是第一笔
                    # 所以新向上段从 prev_same_dir_idx 开始，向下段在 prev_same_dir_idx - 1 结束
                    seg_end_idx = prev_same_dir_idx - 1
                    # 但必须保证向下段至少有 MIN_SEGMENT_PENS 根笔
                    down_seg_pen_count = seg_end_idx - seg_start + 1
                    if down_seg_pen_count >= MIN_SEGMENT_PENS:
                        _close_segment(seg_end_idx, "down")
                        seg_start = prev_same_dir_idx
                        seg_direction = "up"
                        continue

    # 收尾最后一段（仅当剩余笔数 >= MIN_SEGMENT_PENS 时才独立成段）
    remaining_pens = len(pens) - seg_start
    if remaining_pens >= MIN_SEGMENT_PENS:
        _close_segment(len(pens) - 1, seg_direction)
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
    # 若尾部不足3笔且无前一段可合并，则丢弃尾部（无法构成有效段）

    # 后处理校验：消除不合规的段
    segments = validate_segments(segments, pens, klines, MIN_SEGMENT_PENS)

    return segments


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


def calculate_chan_data(klines: List[KlineData], process_include: bool = True, level = DAY) -> dict:
    """
    计算缠论数据

    Args:
        klines: K线数据列表
        process_include: 是否处理包含关系

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
    if process_include:
        processed_klines: List[ClassicChanKline] = process_inclusion(klines)
    else:
        processed_klines = [
            ClassicChanKline(index=i, start=i, end=i, high=k.high, low=k.low)
            for i, k in enumerate(klines)
        ]
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
