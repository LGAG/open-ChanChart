# 缠论三类买卖点 设计方案

> 本文档定义 ChanChart 的三类买卖点（T1/T2/T3）实现方案。沿用 `zhongshu.md` 的标注约定：
> - 【原文】= 缠师《教你炒股票》原文明确（附课程编号）
> - 【工程取舍】= 本项目/开源实现的选择，非缠师原文
>
> 严格区分二者，避免把工程取舍当成缠师本意。本文为**精简方案概要**，伪代码从简，落地时按需细化。

---

## 0. 依赖现状

买卖点建立在已实现的底层构件之上（`backend/app/core/chan_algorithm.py`）：

| 构件 | 现状 | 与买卖点的关系 |
|---|---|---|
| 笔 Pen | `start_index/end_index`（缠论K线索引）、`direction`、`is_sure` | 买卖点的触发载体 |
| 段 Segment | `start_index/end_index`（笔索引）、`top/bottom/direction` | 趋势方向的辅助参考 |
| 中枢 ZhongShu | `start_index/end_index`（缠论K线索引）、`high=ZG`、`low=ZD`、`level=1` | **三类买卖点均围绕中枢定义** |
| 中枢破坏 | `_scan_pens_for_zhongshus` §3.4：离开笔 + 回抽笔，回抽不回 [ZD,ZG] 才破坏 | **T3 的天然基础** |

**关键现状**：代码库**无任何 MACD / 背驰 / 趋势逻辑**（grep 确认仅含包含方向注释）。T1 的背驰判定是全新子系统。

**已确认的工程取舍**（见 plan）：

| 决策点 | 选择 | 理由 |
|---|---|---|
| T1 背驰判定 | **笔幅度背驰**（简化代理，不引 MACD） | 零新依赖、快速落地；偏离原文但可后续替换为 MACD 面积 |
| 离开/回抽笔获取 | **买卖点模块独立重推** | 不改动已验证的 `_scan_pens_for_zhongshus`，零回归 |
| 文档详尽度 | 精简方案概要 | 供快速决策与后续迭代 |

---

## 1. 数据模型

新增 `BuySellPoint`（`backend/app/models/chan_model.py`）：

```python
class BuySellPoint(BaseModel):
    """买卖点数据模型"""
    type: int = Field(..., description="买卖点类型 1/2/3")
    side: str = Field(..., description="方向 buy/sell")
    pen_index: int = Field(..., description="触发笔在 pens 列表的索引")
    chan_kline_index: int = Field(..., description="触发笔极值端的缠论K线索引")
    date: str = Field(..., description="触发日期")
    price: float = Field(..., description="触发价位(笔极值)")
    zhongshu_index: int = Field(..., description="关联中枢在 zhongshus 列表的索引,无关联填 -1")
    is_sure: bool = Field(default=True, description="是否确认(True=确定/False=基于虚拟笔)")
    # T1 专用(其它类型留默认)
    prev_pen_index: int = Field(default=-1, description="T1:前一同向离开笔索引(对比力度用)")
    strength_ratio: float = Field(default=0.0, description="T1:本笔力度/前笔力度(<1=衰减=背驰)")
```

`ChanData` 模型新增 `buy_sell_points: List[BuySellPoint]`。

> `chan_kline_index` 与 Fractal/Pen 同语义（缠论K线索引），前端经 `chan_klines[idx]` 映射回原始K线取日期/价位，沿用中枢绘制的既有模式（见 `KlineChart.vue` 中枢 markArea）。

---

## 2. 公共基础：重推中枢的离开/回抽笔

新增 `_derive_zs_breaks(zhongshus, pens, klines)`，对每个中枢**只读**重推其破坏结构（不改中枢）：

```
对每个 zhongshu z:
  last_in_idx = pens 中 end_index == z.end_index 的笔索引（中枢最后纳入笔，反向笔）
  从 last_in_idx+1 向后扫描第一根全程极值完全脱离 [ZD,ZG] 的笔 = 突破笔
    （整笔在 ZG 上方 = 向上突破；整笔在 ZD 下方 = 向下突破）
  回抽笔 = 突破笔后的反向笔
  回抽是否回区间 = 向上突破: 回抽low<=ZG; 向下突破: 回抽high>=ZD
  确认破坏 = 存在突破笔 且 回抽不回区间
  记录: {z_index, last_in_idx, 突破笔idx, 回抽笔idx, 确认破坏, 突破方向}
```

- **为何扫描而非取 `last_in_idx+1`**：相邻笔共享端点K线，紧邻中枢的笔常被锚定在区间内（仍相交），扫描会把它当延伸吸收；真正的脱离笔可能在其后。扫描第一根脱离笔泛化了 `_scan_pens_for_zhongshus` 两种破坏路径（§3.3 同向笔离开 / §3.4 反向伙伴离开）。
- 全程极值版 `_pen_range_high/_pen_range_low`（`chan_algorithm.py`）与中枢扫描一致，保证回抽判定与破坏逻辑同源。
- 此步纯增量、只读，中枢/段/笔输出不变 → **零回归**（已用基线比对验证）。

---

## 3. 三类买卖点判定规则

### 3.1 T1 —— 背驰反转【工程取舍：笔幅度代理】

**趋势定义【工程取舍】**：≥2 个**同向、依次抬高/降低**的中枢。直接由现有 `zhongshus` 列表按区间相对位置判定，无需走势递归：

```
上涨趋势 = 连续中枢序列 z1,z2,...,zk,满足 z_{i+1}.ZG > z_i.ZG 且 z_{i+1}.ZD > z_i.ZD(依次抬高),k>=2
下跌趋势对称(依次降低)
```

> 原文「走势 = 含中枢的完整走势」是递归概念（`zhongshu.md §0.2`），本方案用「≥2 同向中枢」近似，是工程取舍。

**笔幅度背驰代理**：趋势中**最后一根离开笔**（创趋势新高/新低）的力度 = 笔幅度（`pen_high - pen_low`，全程极值版）**小于**前一根同向离开笔的力度 → 衰减 → 背驰。

```
上涨趋势末端:
  最后离开笔 high == 趋势最高(创新高) 且 力度 < 前同向离开笔力度
  → 顶背驰 → T1 sell @ 离开笔高点
  strength_ratio = 本笔力度 / 前笔力度   (<1 即背驰,可设阈值如 <0.8)
下跌趋势对称 → 底背驰 → T1 buy @ 离开笔低点
```

- **【工程取舍】**：原文背驰用 MACD 红绿柱面积对比（趋势中两段同向次级别走势的 MACD 面积）。本方案用笔幅度作代理，偏离原文、信号质量打折，但零新依赖。后续可替换为 MACD 面积（演进项）。
- **【工程取舍】**：仅做**趋势背驰**，不做盘整背驰（盘整 = 单中枢震荡，本期排除）。

### 3.2 T2 —— 确认不破

T1 反转点之后，**首次反向回抽笔**不回前中枢区间：

```
T1 buy(底背驰) 之后,首根向下笔回抽,其 low 仍 > 前中枢 ZG(不破回中枢上方)
  → T2 buy @ 该回抽笔低点
T1 sell(顶背驰) 对称 → T2 sell @ 回抽笔高点
```

- T2 **依赖 T1 先成立**（同一趋势末端）。该趋势无 T1 信号则无 T2。
- 「不回区间」= 回抽笔全程极值未触及 [ZD,ZG]，与中枢破坏回抽判定同一标准。

### 3.3 T3 —— 突破回抽（直接映射中枢破坏）

中枢被**确认破坏**后（§2 的「确认破坏」），**回抽笔本身即 T3 触发笔**：

```
向上破坏(离开笔向上突破 ZG 上方,回抽笔不回 [ZD,ZG])
  → T3 buy @ 回抽笔低点
向下破坏对称 → T3 sell @ 回抽笔高点
```

- **T3 = 中枢破坏的回抽确认**，是 `_scan_pens_for_zhongshus` §3.4「回抽不进区间→确认破坏」的直接信号化。`zhongshu.md §0.7` 标此为原文间接、§7 列为演进方向。
- 离开/回抽笔由 §2 重推，不动中枢代码。
- 信号最明确、成本最低 → **建议优先实现**。

---

## 4. 接入点

| 层 | 文件 | 改动 |
|---|---|---|
| 模型 | `backend/app/models/chan_model.py` | 新增 `BuySellPoint`；`ChanData` 加 `buy_sell_points` 字段 |
| 算法 | `backend/app/core/chan_algorithm.py` | 新增 `identify_buy_sell_points(pens, segments, zhongshus, klines)`；在 `calculate_chan_data` 末尾（`identify_zhongshus` 之后）调用，返回 dict 加 `"buy_sell_points"` 键 |
| API | `backend/app/api/chan.py` | `data.chan` 加 `"buy_sell_points": [b.model_dump() for b in ...]` |
| 前端图表 | `frontend/src/components/KlineChart.vue` | `seriesToggleBtns` 加一组 `{key:'bspoint', showKey:'bspoints', label:'买卖点'}` + `showBuySellPoints` ref + `seriesHidden.bspoint`；新增 scatter 系列，按 `side` 分色（买=`p.up`、卖=`p.down`）、`type` 标注 1/2/3；坐标 `[date, price]` 经 `chan_klines[chan_kline_index]` 映射 |
| 统计面板 | `frontend/src/views/Home.vue` | stats-panel 增「买卖点数量」（可按 T1/T2/T3 分计） |

> `identify_buy_sell_points` 内部顺序：`_derive_zs_breaks` → 识别趋势 → T1（背驰）→ T2（依赖 T1）→ T3（破坏回抽）。

---

## 5. 验证

1. **类型检查**：`conda run -n ws mypy .`，新增模型/函数零新增类型错误。
2. **T3（最先验证）**：选波动丰富股票，勾「中枢+买卖点」，确认每个 T3 落在某中枢破坏的回抽笔上、方向与突破一致。
3. **T2**：确认 T2 出现在 T1 之后、回抽不破前中枢区间。
4. **T1**：选有明显趋势+末端力度衰减的股票（日线），肉眼核对「创新高/新低 + 笔幅度缩短」处出 T1。**幅度代理可能误报**，需对照实盘调阈值（如 `strength_ratio < 0.8`）。
5. **端到端**：切周期/主题正确重渲染；<3 笔或无中枢时买卖点为空不报错；虚拟笔触发的买卖点 `is_sure=False` 前端区分显示。
6. **回归**：中枢/段/笔输出与改动前一致（买卖点模块纯增量、不碰中枢代码）。

---

## 6. 范围排除（本期不做）

- MACD 面积背驰（T1 仅用笔幅度代理，见 §3.1 工程取舍）。
- 多级别走势递归、中枢级别升级（9段/三中枢重叠）。
- 买卖点后的止损/目标位、确认强度评分。
- T1 的盘整背驰（仅做趋势背驰）。

---

## 7. 分阶段落地建议

| 阶段 | 内容 | 成本 | 状态 | 依据 |
|---|---|---|---|---|
| **P1** | T3（突破回抽） | 最低 | ✅ 已实现 | 直接复用中枢破坏逻辑，重推回抽笔即可，信号最明确 |
| **P2** | T2（确认不破） | 低 | ✅ 已实现 | T1 触发笔后首根反向回抽笔不回最后中枢区间 → 反转确认；与 T3「不回区间」同标准 |
| **P3** | T1（背驰反转） | 中 | ✅ 已实现 | 趋势(≥2同向抬升/降低中枢)+笔幅度衰减代理；阈值 `chan.divergence_ratio` 可调 |

> 三类买卖点均已落地：`_derive_zs_breaks`（重推突破/回抽笔）+ `_identify_t1_t2`（趋势判定+背驰+T2）+ `identify_buy_sell_points`（T3）（`chan_algorithm.py`）。
> - T3 经单元用例（向上/向下突破、回抽回区间不触发、段尾无回抽不触发、延迟突破扫描）+ 基线回归比对验证。
> - T1/T2 经合成用例验证（上涨顶背驰→T1/T2 sell、下跌底背驰→T1/T2 buy、未衰减不触发、单中枢无趋势不触发）。
> - 端到端：600036(招商银行) 2022-01-01~2025-07-25 日K 实测出 T1 sell@2025-05-15(strength_ratio=0.47)+T2 sell@2025-07-10+T3 buy@2025-05-30，前端 ECharts 卖点系列含 3 点(S3/S1/S2)、像素采样确认标记渲染。
> - T1 背驰阈值 `chan.divergence_ratio`（默认 0.8）可对照实盘调参；幅度代理偏离原文 MACD 面积，后续可演进。

---

## 8. 后续演进（参考）

1. **MACD 面积背驰**：替换 T1 的笔幅度代理为原文正统的 MACD 红绿柱面积对比，需新增 MACD 子系统（`KlineData.close` 已具备）。
2. **盘整背驰**：单中枢震荡内的背驰，扩展 T1 覆盖盘整场景。
3. **走势递归 / 级别升级**：多级别中枢与买卖点（9段/三中枢重叠，注意 9 段为后人演绎，见 `zhongshu.md §0.7`）。
4. **买卖点强度评分 / 止损位**：结合中枢区间与力度量化信号质量。
