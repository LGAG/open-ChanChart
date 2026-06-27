# 缠论笔（Pen）算法规范

> 本文档定义缠论中"笔"，供 Claude Code 参考实现。
> 缠论术语：笔=pen，顶分型=top fractal，底分型=bottom fractal，包含关系=inclusion relationship，缠论K线=processed kline（经过包含处理后的K线）

---

## 1. 前置条件

笔的生成依赖于以下前置步骤的输出：

1. **原始K线** → `List[KlineData]`（来自 baostock，含 `date`, `high`, `low` 等字段）
2. **包含关系处理** → `List[ClassicChanKline]`（由 `process_inclusion()` 生成，含 `index`, `start`, `end`, `high`, `low`）
3. **分型识别** → `List[Fractal]`（由 `identify_fractals()` 生成，含 `index`, `k_index`, `date`, `type`）

关键模型定义（`chan_model.py`）：

```python
class ClassicChanKline(BaseModel):
    index: int   # 缠论K线索引（包含处理后重新编号）
    start: int   # 对应原始K线的起始索引
    end: int     # 对应原始K线的结束索引
    high: float  # 最高价
    low: float   # 最低价

class Fractal(BaseModel):
    index: int   # 分型中心所在的缠论K线索引
    k_index: int # 分型中心对应的原始K线索引
    date: str    # 日期
    type: str    # "top" 或 "bottom"

class Pen(BaseModel):
    start_index: int   # 起始缠论K线索引
    end_index: int     # 结束缠论K线索引
    start_date: str    # 起始日期
    end_date: str      # 结束日期
    direction: str     # "up" 或 "down"
```

**重要**：笔的生成函数签名应为：

```python
def generate_pens(fractals: List[Fractal], klines: List[ClassicChanKline]) -> List[Pen]:
```

需要 `klines` 参数来获取分型对应缠论K线的 `high`/`low` 值，用于分型合并时的比较。

---

## 2. 笔的定义

### 2.1 基本定义

**笔**是连接一个顶分型和一个底分型的线段，代表价格从一个极值点到另一个极值点的运动。

- **向上笔**：起始于底分型，终止于顶分型，`direction = "up"`
- **向下笔**：起始于顶分型，终止于底分型，`direction = "down"`

### 2.2 成笔条件

两个相邻分型构成一笔，必须**同时**满足：

| 条件 | 说明 |
|------|------|
| **类型交替** | 两个分型必须一顶一底，不能同为顶分型或同为底分型 |
| **间距足够** | 两个分型中心的缠论K线索引之差>=3，并且两个分型中心缠论k线之间至少需要有3条实际k线 |
| **方向正确** | 上升笔的终点必须严格高于起点，下降笔的终点必须严格低于起点 |

这正是满足条件的最小间距。

### 2.3 缺口成笔（补充规则）

当两个相邻分型之间存在**价格跳空缺口**时，只要满足以下条件即可成一笔。

**缺口判定**：
- 向上笔（底→顶）：底分型中心K线的 `high < 顶分型下一根K线的 low`，即存在向上跳空
  - 更精确地说：`klines[bottom_fractal.index + 1].low > klines[bottom_fractal.index].high`
- 向下笔（顶→底）：顶分型中心K线的 `low > 底分型下一根K线的 high`，即存在向下跳空
  - 更精确地说：`klines[top_fractal.index + 1].high < klines[top_fractal.index].low`

**注意**：缺口成笔是可选增强规则，核心算法应先实现标准间距规则（>= 4），确认正确后再添加缺口支持。


### 2.4 笔的延伸

只有当出现反向笔时，才能认为当前笔结束，否则当前笔一直延伸。
---