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
                # 任一笔涉及虚拟分型则合并后仍为虚拟笔
                prev.is_sure = prev.is_sure and curr.is_sure
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


# ---------------------------------------------------------------------------
# 特征序列相关辅助数据结构
# ---------------------------------------------------------------------------

class CharElement:
    """特征序列元素：将笔视为K线，用于包含处理和分型识别"""

    def __init__(self, pen_indices: List[int], high: float, low: float) -> None:
        self.pen_indices = pen_indices  # 对应 pens 列表中的索引列表（包含处理会合并多个原始笔）
        self.high = high
        self.low = low


class CharFractal:
    """特征序列中的分型"""

    def __init__(self, fractal_type: str, middle_idx: int,
                 first_elem: CharElement, second_elem: CharElement, third_elem: CharElement) -> None:
        self.type = fractal_type       # "top" 或 "bottom"
        self.middle_idx = middle_idx   # 分型中间元素在标准特征序列中的索引
        self.first_elem = first_elem
        self.second_elem = second_elem
        self.third_elem = third_elem


def _build_char_sequence(pens: List[Pen], seg_start: int, seg_direction: str,
                         klines: List[ClassicChanKline]) -> List[CharElement]:
    """
    构建特征序列。

    向上段(seg_direction=="up")的特征序列 = 段内所有向下笔(X序列)
    向下段(seg_direction=="down")的特征序列 = 段内所有向上笔(S序列)

    Args:
        pens: 完整笔列表
        seg_start: 段起始笔索引
        seg_direction: 段方向 "up" 或 "down"
        klines: 缠论K线列表

    Returns:
        特征序列元素列表
    """
    opposite_dir = "down" if seg_direction == "up" else "up"
    elements: List[CharElement] = []
    for i in range(seg_start, len(pens)):
        if pens[i].direction == opposite_dir:
            elements.append(CharElement(
                pen_indices=[i],
                high=pen_high(pens[i], klines),
                low=pen_low(pens[i], klines),
            ))
    return elements


def _process_char_sequence_inclusion(elements: List[CharElement], seg_direction: str = "up") -> List[CharElement]:
    """
    对特征序列进行包含关系处理，生成标准特征序列。

    合并方向整段固定为段方向（不随局部无包含对的相对高低翻转）：
    - 向上段的特征序列（X序列）始终按上升趋势合并 → 取 high 中较高的 high、low 中较高的 low
    - 向下段的特征序列（S序列）始终按下降趋势合并 → 取 high 中较低的 high、low 中较低的 low

    依据：向上段中相邻向上笔 Sᵢ 与 Sᵢ₊₁ 之间必然有重合区间，推动 X 序列低点逐步抬高，
    故整段 X 序列呈上升趋势；向下段对称。因此包含方向整段固定为段方向，避免在见顶回落
    附近被局部相对高低误翻，抹掉本该成型的分型。

    Args:
        elements: 原始特征序列
        seg_direction: 段方向，"up" 或 "down"，决定整段固定的合并方向
    """
    if len(elements) < 2:
        return elements[:]

    result: List[CharElement] = [CharElement(
        pen_indices=elements[0].pen_indices[:],
        high=elements[0].high,
        low=elements[0].low,
    )]
    direction = seg_direction  # 整段固定方向：不随无包含对的相对高低翻转

    for i in range(1, len(elements)):
        curr = elements[i]
        prev = result[-1]

        # 判断包含关系
        is_contained = (curr.high <= prev.high and curr.low >= prev.low) or \
                       (curr.high >= prev.high and curr.low <= prev.low)

        if not is_contained:
            # 无包含关系：直接追加，方向不再更新（整段固定为段方向）
            result.append(CharElement(
                pen_indices=curr.pen_indices[:],
                high=curr.high,
                low=curr.low,
            ))
        else:
            # 有包含关系，按整段固定方向处理
            # 合并 pen_indices：上升取后者的索引（极值在后者），下降取前者的索引（极值在前者）
            if direction == "up":
                new_elem = CharElement(
                    pen_indices=prev.pen_indices + curr.pen_indices,
                    high=max(prev.high, curr.high),
                    low=max(prev.low, curr.low),
                )
            else:
                new_elem = CharElement(
                    pen_indices=prev.pen_indices + curr.pen_indices,
                    high=min(prev.high, curr.high),
                    low=min(prev.low, curr.low),
                )
            result[-1] = new_elem

    return result


def _pens_overlap(pen_a: Pen, pen_b: Pen, klines: List[ClassicChanKline]) -> bool:
    """
    判断两根同方向笔是否有重合区间。

    两根同向笔重合的条件：
    - 向上笔：前一笔的低点 ≤ 后一笔的高点 且 后一笔的低点 ≤ 前一笔的高点
      即 pen_a_low ≤ pen_b_high 且 pen_b_low ≤ pen_a_high
    - 向下笔：同理，high 和 low 的重合判断与方向无关
      即 min(pen_a_high, pen_b_high) ≥ max(pen_a_low, pen_b_low)

    实际上无论方向，重合判断都是：价格区间有交集。
    """
    a_high = pen_high(pen_a, klines)
    a_low = pen_low(pen_a, klines)
    b_high = pen_high(pen_b, klines)
    b_low = pen_low(pen_b, klines)
    # 重合条件：两者价格区间有交集
    return min(a_high, b_high) >= max(a_low, b_low)


def _find_overlaps_break(pens: List[Pen], klines: List[ClassicChanKline],
                         seg_start: int, seg_direction: str) -> int | None:
    """
    在当前段中检查同向笔是否有重合区间。

    向上段 S₁X₁S₂X₂…SₙXₙ：检查 Sᵢ 与 Sᵢ₊₁ 是否有重合，无重合则段终结于 Sᵢ
    向下段 X₁S₁X₂S₂…XₙSₙ：检查 Xᵢ 与 Xᵢ₊₁ 是否有重合，无重合则段终结于 Xᵢ

    Args:
        pens: 完整笔列表
        klines: 缠论K线列表
        seg_start: 段起始笔索引
        seg_direction: 段方向 "up" 或 "down"

    Returns:
        段应结束的笔索引（同向笔无重合处的前一同向笔索引），
        若所有同向笔都有重合则返回 None
    """
    same_dir = seg_direction  # 与段方向相同的笔

    # 收集段内从 seg_start 开始的所有同向笔
    same_dir_indices: List[int] = []
    for i in range(seg_start, len(pens)):
        if pens[i].direction == same_dir:
            same_dir_indices.append(i)

    # 逐对检查相邻同向笔是否有重合
    for k in range(len(same_dir_indices) - 1):
        idx_a = same_dir_indices[k]
        idx_b = same_dir_indices[k + 1]
        if not _pens_overlap(pens[idx_a], pens[idx_b], klines):
            # S_k 与 S_{k+1} 无重合 → 段终结于 S_k
            # 段结束笔索引 = idx_a（S_k 是段的最后一根同向笔）
            # 因为段以同向笔结束，且 S_k 之后不能再有 S_{k+1}
            return idx_a

    return None


def _has_gap(first: CharElement, second: CharElement) -> bool:
    """判断特征序列中两个相邻元素之间是否有缺口（无重合区间）"""
    return first.low > second.high or second.low > first.high


def _identify_char_fractals(std_seq: List[CharElement]) -> List[CharFractal]:
    """
    在标准特征序列中识别分型。

    顶分型：中间元素的 high 是三者最高，low 也是三者最高
    底分型：中间元素的 low 是三者最低，high 也是三者最低
    """
    fractals: List[CharFractal] = []
    if len(std_seq) < 3:
        return fractals

    for i in range(1, len(std_seq) - 1):
        prev_e = std_seq[i - 1]
        curr_e = std_seq[i]
        next_e = std_seq[i + 1]

        # 顶分型
        if (curr_e.high > prev_e.high and curr_e.high > next_e.high and
                curr_e.low > prev_e.low and curr_e.low > next_e.low):
            fractals.append(CharFractal(
                fractal_type="top",
                middle_idx=i,
                first_elem=prev_e,
                second_elem=curr_e,
                third_elem=next_e,
            ))

        # 底分型
        elif (curr_e.low < prev_e.low and curr_e.low < next_e.low and
              curr_e.high < prev_e.high and curr_e.high < next_e.high):
            fractals.append(CharFractal(
                fractal_type="bottom",
                middle_idx=i,
                first_elem=prev_e,
                second_elem=curr_e,
                third_elem=next_e,
            ))

    return fractals


def validate_segments_v1(
    segments: List[Segment], pens: List[Pen], klines: List[ClassicChanKline], min_pens: int = 3
) -> List[Segment]:
    """
    [v1备份] 校验段列表，确保满足缠论定义：
    1. 每段笔数 >= min_pens 且为奇数
    2. 段方向 = 起始笔方向 = 终止笔方向（向上段以向上笔起止，向下段以向下笔起止）
    3. 相邻段方向交替
    4. 相邻段首尾衔接（前一段 end_index + 1 == 后一段 start_index）

    不满足时修复：合并/截断/丢弃，多轮迭代直到收敛。
    """
    if not segments:
        return segments

    def _pen_count(seg: Segment) -> int:
        return seg.end_index - seg.start_index + 1

    def _recalc(seg: Segment) -> None:
        """从段内笔重新计算 top/bottom/direction"""
        seg.top = max(pen_high(pens[i], klines) for i in range(seg.start_index, seg.end_index + 1))
        seg.bottom = min(pen_low(pens[i], klines) for i in range(seg.start_index, seg.end_index + 1))
        seg.direction = pens[seg.start_index].direction

    changed = True
    while changed:
        changed = False
        result: List[Segment] = []

        for seg in segments:
            # 1. 笔数不足 min_pens → 合并到前一段
            if _pen_count(seg) < min_pens:
                if result:
                    result[-1].end_index = seg.end_index
                    _recalc(result[-1])
                    changed = True
                continue

            # 2. 笔数为偶数 → 末尾减1笔使其为奇数
            if _pen_count(seg) % 2 == 0:
                seg.end_index -= 1
                _recalc(seg)
                changed = True
                if _pen_count(seg) < min_pens:
                    if result:
                        result[-1].end_index = seg.end_index + 1
                        _recalc(result[-1])
                    continue

            # 3. 段方向与起始笔方向不一致 → 用起始笔方向覆盖
            if seg.direction != pens[seg.start_index].direction:
                seg.direction = pens[seg.start_index].direction
                changed = True

            # 4. 终止笔方向与段方向不一致 → 末尾减1笔
            if pens[seg.end_index].direction != seg.direction:
                seg.end_index -= 1
                _recalc(seg)
                changed = True
                if _pen_count(seg) < min_pens:
                    if result:
                        result[-1].end_index = seg.end_index + 1
                        _recalc(result[-1])
                    continue

            # 5. 与前段方向相同（平行段）→ 合并到前段
            if result and result[-1].direction == seg.direction:
                result[-1].end_index = seg.end_index
                _recalc(result[-1])
                changed = True
                continue

            # 6. 与前段不衔接 → 调整 start_index 使其衔接
            if result and result[-1].end_index + 1 != seg.start_index:
                seg.start_index = result[-1].end_index + 1
                _recalc(seg)
                changed = True
                if _pen_count(seg) < min_pens:
                    if len(result) >= 2:
                        result[-1].end_index = seg.end_index
                        _recalc(result[-1])
                    else:
                        result[-1].end_index = seg.end_index
                        _recalc(result[-1])
                    continue

            result.append(seg)

        # 处理首段不足的情况
        if result and _pen_count(result[0]) < min_pens:
            if len(result) >= 2:
                first = result.pop(0)
                result[0].start_index = first.start_index
                _recalc(result[0])
                changed = True
            else:
                result.pop(0)
                changed = True

        segments = result

    return segments


def validate_segments(
    segments: List[Segment], pens: List[Pen], klines: List[ClassicChanKline], min_pens: int = 3
) -> List[Segment]:
    """
    校验段列表，确保满足缠论定义：
    1. 每段笔数 >= min_pens 且为奇数
    2. 段方向 = 起始笔方向 = 终止笔方向（向上段以向上笔起止，向下段以向下笔起止）
    3. 相邻段方向交替
    4. 相邻段首尾衔接（前一段 end_index + 1 == 后一段 start_index）

    不满足时修复：合并/截断/丢弃，多轮迭代直到收敛。
    """
    if not segments:
        return segments

    def _pen_count(seg: Segment) -> int:
        return seg.end_index - seg.start_index + 1

    def _recalc(seg: Segment) -> None:
        """从段内笔重新计算 top/bottom/direction"""
        seg.top = max(pen_high(pens[i], klines) for i in range(seg.start_index, seg.end_index + 1))
        seg.bottom = min(pen_low(pens[i], klines) for i in range(seg.start_index, seg.end_index + 1))
        seg.direction = pens[seg.start_index].direction

    changed = True
    while changed:
        changed = False
        result: List[Segment] = []

        for seg in segments:
            # 1. 笔数不足 min_pens → 合并到前一段
            if _pen_count(seg) < min_pens:
                if result:
                    result[-1].end_index = seg.end_index
                    _recalc(result[-1])
                    changed = True
                continue

            # 2. 笔数为偶数 → 末尾减1笔使其为奇数
            if _pen_count(seg) % 2 == 0:
                seg.end_index -= 1
                _recalc(seg)
                changed = True
                if _pen_count(seg) < min_pens:
                    if result:
                        result[-1].end_index = seg.end_index + 1
                        _recalc(result[-1])
                    continue

            # 3. 段方向与起始笔方向不一致 → 用起始笔方向覆盖
            if seg.direction != pens[seg.start_index].direction:
                seg.direction = pens[seg.start_index].direction
                changed = True

            # 4. 终止笔方向与段方向不一致 → 末尾减1笔
            if pens[seg.end_index].direction != seg.direction:
                seg.end_index -= 1
                _recalc(seg)
                changed = True
                if _pen_count(seg) < min_pens:
                    if result:
                        result[-1].end_index = seg.end_index + 1
                        _recalc(result[-1])
                    continue

            # 5. 与前段方向相同（平行段）→ 合并到前段
            if result and result[-1].direction == seg.direction:
                result[-1].end_index = seg.end_index
                _recalc(result[-1])
                changed = True
                continue

            # 6. 与前段不衔接 → 调整 start_index 使其衔接
            if result and result[-1].end_index + 1 != seg.start_index:
                seg.start_index = result[-1].end_index + 1
                _recalc(seg)
                changed = True
                if _pen_count(seg) < min_pens:
                    if len(result) >= 2:
                        result[-1].end_index = seg.end_index
                        _recalc(result[-1])
                    else:
                        result[-1].end_index = seg.end_index
                        _recalc(result[-1])
                    continue

            result.append(seg)

        # 处理首段不足的情况
        if result and _pen_count(result[0]) < min_pens:
            if len(result) >= 2:
                first = result.pop(0)
                result[0].start_index = first.start_index
                _recalc(result[0])
                changed = True
            else:
                result.pop(0)
                changed = True

        segments = result

    return segments
