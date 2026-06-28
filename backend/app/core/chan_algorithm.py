"""缠论核心算法实现"""
from typing import List
from app.models.stock_model import KlineData
from app.models.chan_model import ClassicChanKline, Fractal, Pen, Segment, ZhongShu, DAY


def is_kline_contained(k1: ClassicChanKline, k2: ClassicChanKline) -> bool:
    """
    判断两根K线是否存在包含关系
    包含关系：一根K线的高低点完全包含另一根K线，或被另一根K线包含
    """
    return (k1.high <= k2.high and k1.low >= k2.low) or \
           (k1.high >= k2.high and k1.low <= k2.low)


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
    start = 0
    
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


def generate_pens(fractals: List[Fractal], klines: List[ClassicChanKline]) -> List[Pen]:
    """
    生成笔
    笔是由一个顶分型和一个底分型组成的，且两个分型之间至少间隔一根缠论K线
    """
    if len(fractals) < 2:
        return []
    
    pens = []
    
    left = 0
    right = 1
    
    # 第一步：找到第一根笔
    for i in range(1, len(fractals)):
        # 实际上第一个条件永远成立，但是为了保险起见还是判断一下吧
        if fractals[i].type != fractals[i - 1].type and abs(fractals[i].index - fractals[i - 1].index) >= 4:
            left = i - 1
            right = i
            pens.append(Pen(
                start_index=fractals[left].index,
                end_index=fractals[right].index,
                start_date=fractals[left].date,
                end_date=fractals[right].date,
                direction="up" if fractals[left].type == "bottom" else "down"
            ))
            left += 1
            right += 1
            break
    if len(pens) == 0:
        return []
    # 然后才是逐个处理后面的顶底分型
    while right < len(fractals):
        start_fractal = fractals[left]
        end_fractal = fractals[right]
        print(f"start_fractal: {start_fractal}, end_fractal: {end_fractal}")
        
        # 检查是否符合笔的条件：类型交替且间隔足够
        if start_fractal.type != end_fractal.type and abs(end_fractal.index - start_fractal.index) >= 4:
            direction = "up" if start_fractal.type == "bottom" else "down"
            if direction == pens[-1].direction:
                pens[-1].end_index = end_fractal.index
                pens[-1].end_date = end_fractal.date
            else:
                # 除非有新的反向笔生成，否则一律对最近的一笔进行延伸
                pens.append(Pen(
                    start_index=start_fractal.index,
                    end_index=end_fractal.index,
                    start_date=start_fractal.date,
                    end_date=end_fractal.date,
                    direction=direction
                ))
        else:
            pens[-1].end_index = end_fractal.index
            pens[-1].end_date = end_fractal.date
        left += 1
        right += 1
    
    # 最后一个顶底分型之后的k线暂不做处理，感觉肉眼也能观察出来，可以之后再考虑怎么处理
    return pens

def _can_form_pen(
    start_fractal: Fractal,
    end_fractal: Fractal,
    klines: List[ClassicChanKline],
    prev_pen: Pen | None = None,
) -> bool:
    """
    判断两个分型能否成笔 (§2.2 + §2.3 of pen.md)

    必须同时满足:
    1. 类型交替 — 一顶一底
    2. 间距足够 — 缠论K线索引差 >= 3 且 原始K线间距 >= 4 (之间至少3条实际K线)
    3. 方向正确 — 上升笔终点严格高于起点，下降笔终点严格低于起点

    若间距不足但存在价格跳空缺口 (§2.3)，也可成笔。
    缺口成笔条件：
    - 向上跳空：缺口K线必须是底分型的右侧K线，且缺口完全高于前一笔的最高点
    - 向下跳空：缺口K线必须是顶分型的右侧K线，且缺口完全低于前一笔的最低点
    - 无前一笔时，不允许缺口成笔
    """
    # 1. 类型交替
    if start_fractal.type == end_fractal.type:
        return False

    direction = "up" if start_fractal.type == "bottom" else "down"

    # 2. 间距检查 — 缠论K线索引差和原始K线间距
    chan_gap = abs(end_fractal.index - start_fractal.index)
    raw_gap = abs(klines[end_fractal.index].start - klines[start_fractal.index].end)
    spacing_ok = chan_gap >= 3 and raw_gap >= 4

    # 3. 方向正确性 — 价格必须朝预期方向运动
    if direction == "up":
        price_ok = klines[end_fractal.index].high > klines[start_fractal.index].low
    else:
        price_ok = klines[end_fractal.index].low < klines[start_fractal.index].high

    if spacing_ok and price_ok:
        return True

    # 4. 缺口成笔 (§2.3) — 间距不足时，若存在价格跳空缺口也可成笔
    # 条件：缺口K线必须是分型右侧K线，且缺口完全高于/低于前一笔的最高/最低点
    if not spacing_ok and price_ok and prev_pen is not None:
        if direction == "up":
            # 向上跳空：底分型右侧K线(start_fractal.index + 1)向上跳空
            # 缺口K线即底分型的右侧K线，缺口必须完全高于前一笔的最高点
            if start_fractal.index + 1 < len(klines):
                gap_kline = klines[start_fractal.index + 1]
                if gap_kline.low > klines[start_fractal.index].high:
                    # 存在缺口，检查是否完全高于前一笔最高点
                    if gap_kline.low > _pen_high(prev_pen, klines):
                        return True
        else:
            # 向下跳空：顶分型右侧K线(start_fractal.index + 1)向下跳空
            # 缺口K线即顶分型的右侧K线，缺口必须完全低于前一笔的最低点
            if start_fractal.index + 1 < len(klines):
                gap_kline = klines[start_fractal.index + 1]
                if gap_kline.high < klines[start_fractal.index].low:
                    # 存在缺口，检查是否完全低于前一笔最低点
                    if gap_kline.high < _pen_low(prev_pen, klines):
                        return True

    return False


def generate_new_pens(fractals: List[Fractal], klines: List[ClassicChanKline]) -> List[Pen]:
    """
    生成新笔 (§2.1–§2.4 of pen.md)

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
        if _can_form_pen(fractals[start_idx], fractals[i], klines, prev_pen=None):
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
            if _can_form_pen(start_f, candidate, klines, prev_pen=prev_pen):
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


def _validate_pens(pens: List[Pen], klines: List[ClassicChanKline]) -> List[Pen]:
    """
    校验笔列表，消除平行笔（相邻同方向笔）。

    规则：
    1. 相邻两笔方向必须交替（up/down/up/down...）。
    2. 若出现同方向相邻笔，将后一笔合并到前一笔（延伸终点），
       因为同方向意味着后一笔的终点价格更极端。
    3. 合并后再次校验，直到无平行笔。
    """
    if len(pens) <= 1:
        return pens

    changed = True
    while changed:
        changed = False
        result: List[Pen] = [pens[0]]
        for i in range(1, len(pens)):
            prev = result[-1]
            curr = pens[i]
            if curr.direction == prev.direction:
                # 平行笔：合并到前一笔（延伸终点到更极端位置）
                if curr.direction == "up":
                    # 向上：取更高的终点
                    if klines[curr.end_index].high > klines[prev.end_index].high:
                        prev.end_index = curr.end_index
                        prev.end_date = curr.end_date
                else:
                    # 向下：取更低的终点
                    if klines[curr.end_index].low < klines[prev.end_index].low:
                        prev.end_index = curr.end_index
                        prev.end_date = curr.end_date
                changed = True
            else:
                result.append(curr)
        pens = result

    return pens


def _pen_high(pen: Pen, klines: List[ClassicChanKline]) -> float:
    """获取笔的最高价"""
    if pen.direction == "up":
        return klines[pen.end_index].high
    return klines[pen.start_index].high


def _pen_low(pen: Pen, klines: List[ClassicChanKline]) -> float:
    """获取笔的最低价"""
    if pen.direction == "up":
        return klines[pen.start_index].low
    return klines[pen.end_index].low


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
        top = max(_pen_high(pens[i], klines) for i in range(seg_start, end_idx + 1))
        bottom = min(_pen_low(pens[i], klines) for i in range(seg_start, end_idx + 1))
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
                if _pen_high(pen, klines) < _pen_high(prev_same_dir, klines) and \
                   _pen_low(pen, klines) < _pen_low(prev_same_dir, klines):
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
                if _pen_high(pen, klines) > _pen_high(prev_same_dir, klines) and \
                   _pen_low(pen, klines) > _pen_low(prev_same_dir, klines):
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
            max(_pen_high(pens[i], klines) for i in range(seg_start, len(pens)))
        )
        segments[-1].bottom = min(
            segments[-1].bottom,
            min(_pen_low(pens[i], klines) for i in range(seg_start, len(pens)))
        )
    # 若尾部不足3笔且无前一段可合并，则丢弃尾部（无法构成有效段）

    # 后处理校验：消除不合规的段
    segments = _validate_segments(segments, pens, klines, MIN_SEGMENT_PENS)

    return segments


def _validate_segments(
    segments: List[Segment], pens: List[Pen], klines: List[ClassicChanKline], min_pens: int = 3
) -> List[Segment]:
    """
    校验段列表，修复以下问题：
    1. 段内笔数不足min_pens根 → 合并到前一段
    2. 段方向与实际价格走势矛盾 → 翻转方向
       - 向上段：实际最高价所在的笔索引 应 > 实际最低价所在的笔索引（高点在低点之后）
       - 向下段：实际最低价所在的笔索引 应 > 实际最高价所在的笔索引（低点在高点之后）
       - 若矛盾，说明方向标注错误，翻转方向
    3. 相邻段方向相同（平行段）→ 合并到前一段
    """
    if not segments:
        return segments

    def _find_top_bottom_indices(seg: Segment):
        """找到段内实际最高价和最低价所在的笔索引"""
        top_idx = seg.start_index
        bottom_idx = seg.start_index
        top_val = _pen_high(pens[seg.start_index], klines)
        bottom_val = _pen_low(pens[seg.start_index], klines)
        for i in range(seg.start_index + 1, seg.end_index + 1):
            h = _pen_high(pens[i], klines)
            l = _pen_low(pens[i], klines)
            if h > top_val:
                top_val = h
                top_idx = i
            if l < bottom_val:
                bottom_val = l
                bottom_idx = i
        return top_idx, bottom_idx

    def _fix_direction(seg: Segment) -> None:
        """根据实际价格走势修正段方向"""
        top_idx, bottom_idx = _find_top_bottom_indices(seg)
        if seg.direction == "up" and top_idx < bottom_idx:
            seg.direction = "down"
        elif seg.direction == "down" and bottom_idx < top_idx:
            seg.direction = "up"

    result: List[Segment] = []

    for seg in segments:
        # 段内笔数不足min_pens根 → 合并到前一段
        pen_count = seg.end_index - seg.start_index + 1
        if pen_count < min_pens and result:
            prev = result[-1]
            prev.end_index = seg.end_index
            prev.top = max(prev.top, seg.top)
            prev.bottom = min(prev.bottom, seg.bottom)
            _fix_direction(prev)
            continue

        # 段方向与实际价格走势矛盾 → 翻转方向
        _fix_direction(seg)

        # 平行段：与前一段方向相同 → 合并到前一段
        if result and result[-1].direction == seg.direction:
            prev = result[-1]
            prev.end_index = seg.end_index
            prev.top = max(prev.top, seg.top)
            prev.bottom = min(prev.bottom, seg.bottom)
            _fix_direction(prev)
            continue

        result.append(seg)

    # 后处理：如果第一段笔数不足，合并到第二段
    if len(result) >= 2 and (result[0].end_index - result[0].start_index + 1) < min_pens:
        first = result.pop(0)
        result[0].start_index = first.start_index
        result[0].top = max(first.top, result[0].top)
        result[0].bottom = min(first.bottom, result[0].bottom)
        _fix_direction(result[0])

    # 移除仍然不足min_pens根笔的首段（无法合并也无法补足）
    if result and (result[0].end_index - result[0].start_index + 1) < min_pens:
        result.pop(0)

    return result


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

        high1 = _pen_high(pen1, klines)
        low1 = _pen_low(pen1, klines)
        high2 = _pen_high(pen2, klines)
        low2 = _pen_low(pen2, klines)
        high3 = _pen_high(pen3, klines)
        low3 = _pen_low(pen3, klines)

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
    
    # 1. 处理包含关系
    if process_include:
        processed_klines = process_inclusion(klines)
    else:
        processed_klines = klines
    print(f"processed_klines: \n")
    for kline in processed_klines:
        print(kline)
    # 2. 识别分型
    fractals = identify_fractals(processed_klines, klines)
    
    # 3. 生成笔并校验（消除平行笔）
    pens = generate_new_pens(fractals, processed_klines)
    pens = _validate_pens(pens, processed_klines)

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
