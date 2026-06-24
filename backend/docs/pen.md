# 缠论笔（Pen）算法规范

> 本文档定义缠论中"笔"的正确算法，供 Claude Code 参考实现。
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
| **间距足够** | 两个分型中心的缠论K线索引之差 `\|index₁ - index₂\| >= 4` |

**间距条件的推导**：

每个分型占据 3 根缠论K线（左K线、中心K线、右K线）。两个分型之间不能共享K线，且中间至少要有 1 根独立K线：

```
分型A:         [左_A, 中心_A, 右_A]
独立K线:                              [独立]
分型B:                                       [左_B, 中心_B, 右_B]

中心索引差 = 右_A索引 + 1 + 1 + 左_B偏移 - 中心_A索引
           >= (中心_A + 1) + 1 + 1 - 中心_A
           >= 3 ... 但需要至少1根独立K线
```

当中心索引差 = 4 时：
```
K线位置:  ... [i-1] [i] [i+1] [i+2] [i+3] [i+4] ...
分型A:          左    中心   右
独立K线:                     [独立]
分型B:                              左    中心
```

这正是满足条件的最小间距。

### 2.3 缺口成笔（补充规则）

当两个相邻分型之间存在**价格跳空缺口**时，间距条件可放宽为 `|index₁ - index₂| >= 3`。

**缺口判定**：
- 向上笔（底→顶）：底分型中心K线的 `high < 顶分型下一根K线的 low`，即存在向上跳空
  - 更精确地说：`klines[bottom_fractal.index + 1].low > klines[bottom_fractal.index].high`
- 向下笔（顶→底）：顶分型中心K线的 `low > 底分型下一根K线的 high`，即存在向下跳空
  - 更精确地说：`klines[top_fractal.index + 1].high < klines[top_fractal.index].low`

**注意**：缺口成笔是可选增强规则，核心算法应先实现标准间距规则（>= 4），确认正确后再添加缺口支持。

---

## 3. 笔的生成算法

### 3.1 总体流程

```
输入: fractals（按缠论K线时间顺序排列的分型列表）, klines（缠论K线列表）
输出: pens（笔列表）

步骤:
  1. 分型预处理：合并相邻同类型分型，确保严格交替
  2. 间距校验：移除不满足间距条件的分型，重新合并
  3. 连接成笔：将相邻的顶底分型对连接为笔
```

### 3.2 Step 1：分型合并

`identify_fractals()` 的输出可能包含相邻同类型分型（两个顶分型之间没有底分型，或反之）。在生成笔之前，必须将它们合并为严格交替的序列。

**合并规则**：
- 相邻两个**顶分型**：保留 `klines[fractal.index].high` 更高的那个，删除另一个
- 相邻两个**底分型**：保留 `klines[fractal.index].low` 更低的那个，删除另一个

**算法**：

```
function merge_fractals(fractals, klines):
    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(fractals) - 1:
            if fractals[i].type == fractals[i+1].type:
                # 同类型分型，需要合并
                if fractals[i].type == "top":
                    # 顶分型：保留高点更高的
                    if klines[fractals[i+1].index].high >= klines[fractals[i].index].high:
                        删除 fractals[i]
                    else:
                        删除 fractals[i+1]
                else:  # "bottom"
                    # 底分型：保留低点更低的
                    if klines[fractals[i+1].index].low <= klines[fractals[i].index].low:
                        删除 fractals[i]
                    else:
                        删除 fractals[i+1]
                changed = True
                # 不递增 i，因为删除后需要重新检查当前位置
            else:
                i += 1
    return fractals
```

**示例**：

```
原始分型序列: B₁ T₁ T₂ B₂ T₃ B₃

T₁ 和 T₂ 相邻同类型:
  若 klines[T₂].high > klines[T₁].high → 删除 T₁
  结果: B₁ T₂ B₂ T₃ B₃  (严格交替 ✓)
```

### 3.3 Step 2：间距校验

合并后的分型序列虽然严格交替，但相邻分型可能间距不足（< 4）。需要进一步处理。

**处理规则**：

对于每对相邻分型，如果 `|index₁ - index₂| < 4`：

1. 比较这对分型与各自相邻的另一侧分型
2. 移除"不够极端"的那个分型（即对笔的构成贡献较小的）
3. 移除后，序列可能不再交替，需要回到 Step 1 重新合并

**"不够极端"的判定**：
- 如果顶分型间距不足：移除 `high` 较低的顶分型
- 如果底分型间距不足：移除 `low` 较高的底分型

**注意**：当间距不足的分型对涉及序列首尾时，优先移除靠近首尾的分型。

**算法**：

```
function validate_spacing(fractals, klines):
    # 与 merge_fractals 交替执行，直到稳定
    prev_count = -1
    while len(fractals) != prev_count:
        prev_count = len(fractals)
        fractals = merge_fractals(fractals, klines)

        i = 0
        while i < len(fractals) - 1:
            if abs(fractals[i+1].index - fractals[i].index) < 4:
                # 间距不足，需要移除一个分型
                # 策略：比较两个分型的"极端程度"
                removed = remove_less_extreme(fractals, i, i+1, klines)
                # 移除后 break，重新开始循环（因为序列可能不再交替）
                break
            i += 1
    return fractals

function remove_less_extreme(fractals, i, j, klines):
    # i, j 是间距不足的相邻分型索引（一顶一底）
    # 移除对笔贡献较小的那个

    # 如果 i 是第一个分型或 j 是最后一个分型，优先移除边界分型
    if i == 0:
        删除 fractals[i]
        return
    if j == len(fractals) - 1:
        删除 fractals[j]
        return

    # 比较分型与相邻同类型分型的极端程度
    # 顶分型：比较 high；底分型：比较 low
    # 移除相对不极端的那个
    ...
```

**简化策略**（推荐首次实现采用）：

间距校验逻辑较复杂，可采用以下简化策略——在分型合并阶段就考虑间距，将间距不足的同侧分型也纳入合并逻辑：

```
function preprocess_fractals(fractals, klines):
    # 反复合并直到序列稳定（严格交替 + 间距 >= 4）
    changed = True
    while changed:
        changed = False
        fractals = merge_adjacent_same_type(fractals, klines)  # 合并同类型
        fractals, changed = remove_close_pairs(fractals, klines)  # 移除间距不足的
    return fractals
```

### 3.4 Step 3：连接成笔

经过预处理后，分型序列严格交替且间距 >= 4，直接连接相邻分型对即可：

```
function connect_pens(fractals, klines):
    pens = []
    for i in range(0, len(fractals) - 1):
        f1 = fractals[i]
        f2 = fractals[i + 1]

        # 预处理后应严格交替，这里做断言检查
        assert f1.type != f2.type, f"分型未交替: {f1} vs {f2}"

        # 预处理后间距应足够，这里做断言检查
        assert abs(f2.index - f1.index) >= 4, f"间距不足: {f1} vs {f2}"

        direction = "up" if f1.type == "bottom" else "down"
        pens.append(Pen(
            start_index=f1.index,
            end_index=f2.index,
            start_date=f1.date,
            end_date=f2.date,
            direction=direction
        ))
    return pens
```

### 3.5 完整算法伪代码

```python
def generate_pens(fractals: List[Fractal], klines: List[ClassicChanKline]) -> List[Pen]:
    """
    生成笔

    算法步骤:
    1. 合并相邻同类型分型，确保序列严格交替
    2. 移除间距不足的分型对，重新合并
    3. 连接相邻分型对成笔
    """
    if len(fractals) < 2:
        return []

    # Step 1 & 2: 分型预处理（合并 + 间距校验，循环直到稳定）
    processed_fractals = preprocess_fractals(fractals, klines)

    if len(processed_fractals) < 2:
        return []

    # Step 3: 连接成笔
    pens = connect_pens(processed_fractals, klines)

    return pens
```

---

## 4. 当前实现的问题

当前代码中存在两个笔生成函数：

| 函数 | 状态 | 问题 |
|------|------|------|
| `generate_pens()` | **死代码**，未被调用 | 间距检查用 `>= 4`，但同方向延伸逻辑有问题 |
| `generate_new_pens()` | **实际使用** | 间距检查用 `>= 3`，缺口逻辑复杂且可能有误 |

### 4.1 `generate_pens()` 的问题

```python
# 第 188 行：同方向延伸逻辑
if direction == pens[-1].direction:
    pens[-1].end_index = end_fractal.index
    pens[-1].end_date = end_fractal.date
```

**问题**：当新的分型与最后一笔方向相同时，直接延伸最后一笔的终点，但没有检查这个延伸是否合理（新分型是否比当前终点更极端）。

### 4.2 `generate_new_pens()` 的问题

1. **间距条件错误**（第 253 行）：
   ```python
   abs(end_fractal.index - start_fractal.index) >= 3
   ```
   标准成笔条件应为 `>= 4`，`>= 3` 仅在缺口成笔时适用。

2. **间距条件不一致**：`find_first_pen()` 使用了两个条件（缠论K线索引差 >= 3 且原始K线索引差 >= 4），而主循环中只使用缠论K线索引差 >= 3。

3. **缺口逻辑混乱**（第 268 行）：
   ```python
   elif (pens[-1].direction == "up" and end_fractal.type == "bottom"
         and klines[start_fractal.index + 1].high <= klines[pens[-1].start_index].low) or ...
   ```
   条件判断涉及 `start_fractal`、`end_fractal` 和 `pens[-1]` 三者的关系，逻辑难以验证正确性。

4. **"破坏"逻辑复杂**（第 283-310 行）：当反向分型超过当前笔起点时，会删除最后一笔并重新寻找。这个逻辑试图处理笔被破坏的情况，但实现复杂且缺乏注释，容易出错。

5. **缺少分型预处理**：没有在生成笔之前进行分型合并，导致同类型分型需要在主循环中处理，增加了复杂性。

### 4.3 `Pen` 模型缺少价格字段

`Pen` 模型没有 `start_price` / `end_price` 字段，导致 `identify_zhongshus()` 中访问 `pen.start_price` 和 `pen.end_price` 时会报错（CODE_REVIEW.md C2）。

**建议**：为 `Pen` 模型添加价格字段，或在生成笔时通过 `klines[pen.start_index]` / `klines[pen.end_index]` 获取价格。

---

## 5. 推荐实现方案

### 5.1 重构策略

推荐采用 **"先预处理，再连接"** 的两阶段方案，替代当前的 **"边遍历边处理"** 方案：

| 方案 | 优点 | 缺点 |
|------|------|------|
| 边遍历边处理（当前） | 一次遍历 | 逻辑复杂，难以验证 |
| **先预处理再连接（推荐）** | 逻辑清晰，易于测试 | 需要额外的预处理步骤 |

### 5.2 函数设计

```python
def merge_fractals(fractals: List[Fractal], klines: List[ClassicChanKline]) -> List[Fractal]:
    """合并相邻同类型分型，返回严格交替的分型序列"""

def remove_close_fractals(fractals: List[Fractal], klines: List[ClassicChanKline]) -> List[Fractal]:
    """移除间距不足的分型对，返回满足间距条件的分型序列"""

def preprocess_fractals(fractals: List[Fractal], klines: List[ClassicChanKline]) -> List[Fractal]:
    """分型预处理：循环执行合并和间距校验直到稳定"""

def generate_pens(fractals: List[Fractal], klines: List[ClassicChanKline]) -> List[Pen]:
    """生成笔（主入口函数）"""
```

### 5.3 `remove_close_fractals` 详细算法

当发现相邻分型间距 < 4 时，需要决定移除哪一个。推荐策略：

```
对于间距不足的相邻分型对 (f₁, f₂)：

1. 如果 f₁ 是序列的第一个分型 → 移除 f₁
2. 如果 f₂ 是序列的最后一个分型 → 移除 f₂
3. 否则，检查 f₁ 的前一个分型 f₀ 和 f₂ 的后一个分型 f₃：
   - 如果 f₁ 是顶分型且 f₃ 也是顶分型：
     比较 klines[f₁.index].high 和 klines[f₃.index].high
     移除 high 较低的那个
   - 如果 f₁ 是底分型且 f₃ 也是底分型：
     比较 klines[f₁.index].low 和 klines[f₃.index].low
     移除 low 较高的那个
   - 其他情况：移除 f₂（保留更早的分型）
```

### 5.4 测试用例

以下是必须通过的测试场景：

#### 测试 1：基本交替分型

```
K线序列（处理后）: K₀ K₁ K₂ K₃ K₄ K₅ K₆ K₇ K₈ K₉
分型:              B(0)      T(4)      B(8)
                    底       顶         底

间距: |4-0|=4 ✓, |8-4|=4 ✓
预期笔: [B(0)→T(4), up], [T(4)→B(8), down]
```

#### 测试 2：相邻同类型分型需合并

```
分型: B(0) T(4) T(6) B(10)

T(4) 和 T(6) 同类型，需合并：
  若 klines[6].high > klines[4].high → 保留 T(6)
合并后: B(0) T(6) B(10)
间距: |6-0|=6 ✓, |10-6|=4 ✓
预期笔: [B(0)→T(6), up], [T(6)→B(10), down]
```

#### 测试 3：间距不足需移除

```
分型: B(0) T(2) B(6) T(10)

|2-0|=2 < 4，间距不足
B(0) 是第一个 → 移除 B(0)
剩余: T(2) B(6) T(10)
间距: |6-2|=4 ✓, |10-6|=4 ✓
预期笔: [T(2)→B(6), down], [B(6)→T(10), up]
```

#### 测试 4：合并后间距仍不足

```
分型: B(0) T(2) B(3) T(7)

T(2) 和 B(3) 间距 |3-2|=1 < 4
移除 B(3)（非边界，但 T(2) 前面还有 B(0)）
剩余: B(0) T(2) T(7) → 合并同类型
  保留 high 更高的 T
合并后: B(0) T(7)
间距: |7-0|=7 ✓
预期笔: [B(0)→T(7), up]
```

#### 测试 5：空输入和边界情况

```
fractals = [] → pens = []
fractals = [T(0)] → pens = []  # 单个分型无法成笔
fractals = [T(0), B(1)] → pens = []  # 间距不足
fractals = [T(0), B(4)] → pens = [T(0)→B(4), down]  # 最小间距刚好满足
```

#### 测试 6：复杂序列

```
分型: B(0) T(4) B(8) T(9) B(13) T(17)

T(9) 和 B(8) 间距 |9-8|=1 < 4
T(9) 和 B(13) 间距 |13-9|=4 ✓
B(8) 和 T(4) 间距 |8-4|=4 ✓

T(9) 和 B(8) 间距不足：需移除一个
  T(9) 前面有 B(8)，B(8) 前面有 T(4)
  T(4) 和 T(9) 同类型，若 klines[9].high > klines[4].high → 保留 T(9)
  移除 T(4)？不，间距不足的是 B(8) 和 T(9)
  应移除"不够极端"的：比较 B(8) 和其相邻底分型...

（这类复杂场景需要仔细验证，推荐用实际股票数据测试）
```

---

## 6. 与前端渲染的配合

笔数据由后端 `/api/chan/analysis` 接口返回，前端 `KlineChart.vue` 渲染笔的逻辑：

```javascript
// 当前实现（第 55-68 行）
props.chanData.pens.forEach(pen => {
    const startKline = props.chanData.chan_klines[pen.start_index]
    const endKline = props.chanData.chan_klines[pen.end_index]
    // 用 startKline.start 和 endKline.end 定位 x 轴
    // 用 klineData[startKline.start].low / klineData[endKline.end].high 定位 y 轴
})
```

**注意**：
- `pen.start_index` 和 `pen.end_index` 是**缠论K线索引**，对应 `chan_klines` 数组的下标
- 从 `chan_klines[index]` 获取 `start`/`end` 字段（原始K线索引范围），再映射到 `klineData` 获取价格
- 向上笔的起点 y 坐标应取底分型的 `low`，终点 y 坐标应取顶分型的 `high`
- 向下笔的起点 y 坐标应取顶分型的 `high`，终点 y 坐标应取底分型的 `low`

---

## 7. 实现检查清单

实现新的 `generate_pens()` 时，请确保：

- [ ] 删除旧的 `generate_pens()`（第 148-207 行，死代码）
- [ ] 将 `generate_new_pens()` 重命名为 `generate_pens()` 或用新实现替换
- [ ] 删除 `find_first_pen()` 辅助函数（如果新实现不再需要）
- [ ] 新函数签名：`generate_pens(fractals: List[Fractal], klines: List[ClassicChanKline]) -> List[Pen]`
- [ ] 实现 `merge_fractals()` 辅助函数
- [ ] 实现 `preprocess_fractals()` 辅助函数（合并 + 间距校验循环）
- [ ] 标准间距条件：`abs(f1.index - f2.index) >= 4`
- [ ] 缺口成笔作为可选增强（先确保标准规则正确）
- [ ] 移除所有 debug `print` 语句
- [ ] 类型标注完整，通过 `mypy` 检查
- [ ] `calculate_chan_data()` 中调用更新后的函数名
- [ ] 编写单元测试覆盖第 5 节的测试用例
- [ ] 验证前端渲染正常（笔的起止点位置正确）
