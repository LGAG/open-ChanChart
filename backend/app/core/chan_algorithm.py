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
        start=klines[0].date,
        end=klines[0].date,
        high=klines[0].high,
        low=klines[0].low
    )
    processed = [first]
    direction = None  # 'up' or 'down'
    count = 0
    
    for i in range(1, len(klines)):
        current = ClassicChanKline(
            index=i,
            start=klines[i].date,
            end=klines[i].date,
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


def identify_fractals(klines: List[ClassicChanKline]) -> List[Fractal]:
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
            fractals.append(Fractal(
                index=curr_k.index,
                type="top"
            ))
        
        # 底分型判断
        elif (curr_k.low < prev_k.low and curr_k.low < next_k.low and
              curr_k.high < prev_k.high and curr_k.high < next_k.high):
            fractals.append(Fractal(
                index=curr_k.index,
                type="bottom"
            ))
    
    return fractals


def generate_pens(fractals: List[Fractal], klines: List[ClassicChanKline]) -> List[Pen]:
    """
    生成笔
    笔是由一个顶分型和一个底分型组成的，且两个分型之间至少间隔一根K线
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
                start_date=klines[fractals[left].index].start,
                end_date=klines[fractals[right].index].end,
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
                pens[-1].end_date = klines[end_fractal.index].end
            else:
                # 除非有新的反向笔生成，否则一律对最近的一笔进行延申
                pens.append(Pen(
                    start_index=start_fractal.index,
                    end_index=end_fractal.index,
                    start_date=klines[start_fractal.index].start,
                    end_date=klines[end_fractal.index].end,
                    direction=direction
                ))
        else:
            pens[-1].end_index = end_fractal.index
            pens[-1].end_date = klines[end_fractal.index].end
        left += 1
        right += 1
    
    # 最后一个顶底分型之后的k线暂不做处理，感觉肉眼也能观察出来，可以之后再考虑怎么处理
    return pens


def generate_segments(pens: List[Pen]) -> List[Segment]:
    """
    生成段
    简化实现：连续的同向笔可以合并成段
    """
    if len(pens) < 3:
        return []
    
    segments = []
    segment_pens = [pens[0]]
    segment_start_idx = 0
    
    for i in range(1, len(pens)):
        if pens[i].direction == segment_pens[-1].direction:
            segment_pens.append(pens[i])
        else:
            if len(segment_pens) >= 3:
                segments.append(Segment(
                    start_index=segment_start_idx,
                    end_index=segment_start_idx + len(segment_pens) - 1,
                    pens=segment_pens,
                    direction=segment_pens[0].direction
                ))
            segment_start_idx = i
            segment_pens = [pens[i]]
    
    # 处理最后一段
    if len(segment_pens) >= 3:
        segments.append(Segment(
            start_index=segment_start_idx,
            end_index=segment_start_idx + len(segment_pens) - 1,
            pens=segment_pens,
            direction=segment_pens[0].direction
        ))
    
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
    fractals = identify_fractals(processed_klines)
    
    # 3. 生成笔
    pens = generate_pens(fractals, processed_klines)
    
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
