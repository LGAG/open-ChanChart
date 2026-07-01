"""缠论辅助函数：包含判断、笔校验、段校验等工具函数"""
from typing import List
from app.models.chan_model import ClassicChanKline, Fractal, Pen, Segment, DAY


def is_kline_contained(k1: ClassicChanKline, k2: ClassicChanKline) -> bool:
    """
    判断两根K线是否存在包含关系
    包含关系：一根K线的高低点完全包含另一根K线，或被另一根K线包含
    """
    return (k1.high <= k2.high and k1.low >= k2.low) or \
           (k1.high >= k2.high and k1.low <= k2.low)


def _can_form_pen_v1(
    start_fractal: Fractal,
    end_fractal: Fractal,
    klines: List[ClassicChanKline],
    prev_pen: Pen | None = None,
) -> bool:
    """
    [v1备份] 判断两个分型能否成笔 (§2.2 + §2.3 of pen.md)

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
                    if gap_kline.low > pen_high(prev_pen, klines):
                        return True
        else:
            # 向下跳空：顶分型右侧K线(start_fractal.index + 1)向下跳空
            # 缺口K线即顶分型的右侧K线，缺口必须完全低于前一笔的最低点
            if start_fractal.index + 1 < len(klines):
                gap_kline = klines[start_fractal.index + 1]
                if gap_kline.high < klines[start_fractal.index].low:
                    # 存在缺口，检查是否完全低于前一笔最低点
                    if gap_kline.high < pen_low(prev_pen, klines):
                        return True

    return False


def _can_form_pen(
    f1: Fractal,
    f2: Fractal,
    klines: List[ClassicChanKline],
) -> bool:
    """
    判断两个不同类型的分型能否成笔。

    条件：
    1. 缠论K线索引之差 >= 3（中间至少两条缠论K线）
    2. 两个分型之间至少3条实际K线
    """
    # 条件1：缠论K线索引差 >= 3
    if abs(f2.index - f1.index) < 3:
        return False

    # 条件2：两个分型的缠论K线之间至少3条实际K线
    # klines[f2].start - klines[f1].end 为间距，间距 >= 4 表示中间至少3条实际K线
    # (中间实际K线数量 = start - end - 1，>= 3 即 start - end >= 4)
    if klines[f2.index].start - klines[f1.index].end < 4:
        return False

    return True


def generate_pens(fractals: List[Fractal], klines: List[ClassicChanKline]) -> List[Pen]:
    """
    生成笔（旧版算法，已由 generate_new_pens 替代）
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


def validate_pens(pens: List[Pen], klines: List[ClassicChanKline]) -> List[Pen]:
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


def pen_high(pen: Pen, klines: List[ClassicChanKline]) -> float:
    """获取笔的最高价"""
    if pen.direction == "up":
        return klines[pen.end_index].high
    return klines[pen.start_index].high


def pen_low(pen: Pen, klines: List[ClassicChanKline]) -> float:
    """获取笔的最低价"""
    if pen.direction == "up":
        return klines[pen.start_index].low
    return klines[pen.end_index].low


def validate_segments(
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
        top_val = pen_high(pens[seg.start_index], klines)
        bottom_val = pen_low(pens[seg.start_index], klines)
        for i in range(seg.start_index + 1, seg.end_index + 1):
            h = pen_high(pens[i], klines)
            l = pen_low(pens[i], klines)
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
