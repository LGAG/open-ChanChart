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
) -> bool:
    """
    判断两个分型能否成笔 (§2.2 + §2.3 of pen.md)

    必须同时满足:
    1. 类型交替 — 一顶一底
    2. 间距足够 — 缠论K线索引差 >= 3 且 原始K线间距 >= 4 (之间至少3条实际K线)
    3. 方向正确 — 上升笔终点严格高于起点，下降笔终点严格低于起点

    若间距不足但存在价格跳空缺口 (§2.3)，也可成笔。
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
    if not spacing_ok and price_ok:
        if direction == "up":
            # 向上笔：底分型中心K线的下一根K线向上跳空
            if start_fractal.index + 1 < len(klines):
                if klines[start_fractal.index + 1].low > klines[start_fractal.index].high:
                    return True
        else:
            # 向下笔：顶分型中心K线的下一根K线向下跳空
            if start_fractal.index + 1 < len(klines):
                if klines[start_fractal.index + 1].high < klines[start_fractal.index].low:
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
    """
    if len(fractals) < 2:
        return []

    pens: List[Pen] = []

    # 阶段1：找到第一笔作为引导
    start_idx = 0
    found_first = False
    for i in range(1, len(fractals)):
        if _can_form_pen(fractals[start_idx], fractals[i], klines):
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
            # 反向分型 — 尝试成笔
            if _can_form_pen(start_f, candidate, klines):
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
    简化实现：如果发现了更高（低）的高点和更高（低）的低点，那么就认为向上（下）线段延伸，否则，就认为线段结束
    """
    if len(pens) < 3:
        return []
    
    segments = []
    current_idx = 0

    # 首先寻找第一个线段
    for i in range(current_idx, len(pens) - 2):
        if pens[i].direction == 'up' and klines[pens[i+2].start_index].low >= klines[pens[i].start_index].low and klines[pens[i+2].end_index].high >= klines[pens[i].end_index].high:
            current_idx = i + 3
            segments.append(Segment(
                start_index=i,
                end_index=i+2,
                top=klines[pens[i+2].end_index].high,
                bottom=klines[pens[2].start_index].low,
                direction='up'
            ))
            break
        elif pens[i].direction == 'down' and klines[pens[i+2].start_index].low <= klines[pens[i].start_index].low and klines[pens[i+2].end_index].high <= klines[pens[i].end_index].high:
            current_idx = i + 3
            segments.append(Segment(
                start_index=i,
                end_index=i+2,
                top=klines[pens[i].start_index].high,
                bottom=klines[pens[i+2].end_index].low,
                direction='up'
            ))
            break
    if len(segments) == 0:
        print("warning: 没有找到第一个线段")
        return segments

    # 然后寻找后续的线段
    while current_idx < len(pens) - 2:
        if segments[-1].direction == 'up':
            if klines[pens[current_idx+2].start_index].low <= klines[pens[current_idx].start_index].low and klines[pens[current_idx+2].end_index].high <= klines[pens[current_idx].end_index].high:
                segments.append(Segment(
                    start_index=current_idx,
                    end_index=current_idx+2,
                    top=klines[pens[current_idx].start_index].high,
                    bottom=klines[pens[current_idx+2].end_index].low,
                    direction='down'
                ))
                current_idx += 3
                continue
        if segments[-1].direction == 'down':
            if klines[pens[current_idx+2].start_index].low >= klines[pens[current_idx].start_index].low and klines[pens[current_idx+2].end_index].high >= klines[pens[current_idx].end_index].high:
                segments.append(Segment(
                    start_index=current_idx,
                    end_index=current_idx+2,
                    top=klines[pens[current_idx+2].end_index].high,
                    bottom=klines[pens[current_idx].start_index].low,
                    direction='up'
                ))
                current_idx += 3
                continue
        segments[-1].end_index = current_idx + 2
        current_idx += 2
    
    return segments


def identify_zhongshus(pens: List[Pen], level = DAY) -> List[ZhongShu]:
    """
    识别中枢
    简化实现：至少三笔重叠的区域构成中枢
    """
    if len(pens) < 3:
        return []
    
    zhongshus = []
    
    for i in range(len(pens) - 2):
        pen1, pen2, pen3 = pens[i], pens[i + 1], pens[i + 2]
        
        # 计算重叠区域
        high1 = max(pen1.start_price, pen1.end_price)
        low1 = min(pen1.start_price, pen1.end_price)
        high2 = max(pen2.start_price, pen2.end_price)
        low2 = min(pen2.start_price, pen2.end_price)
        high3 = max(pen3.start_price, pen3.end_price)
        low3 = min(pen3.start_price, pen3.end_price)
        
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
    
    # 3. 生成笔
    pens = generate_new_pens(fractals, processed_klines)
    
    return{
        "chan_klines": processed_klines,
        "fractals": fractals,
        "pens": pens
    }
    
    # 4. 生成段
    segments = generate_segments(pens)
    
    # 5. 识别中枢
    zhongshus = identify_zhongshus(pens, level)
    
    return {
        "fractals": fractals,
        "pens": pens,
        "segments": segments,
        "zhongshus": zhongshus
    }
