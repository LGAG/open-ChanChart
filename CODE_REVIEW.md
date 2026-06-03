# ChanChart 代码审查报告

> 审查日期：2026-06-03
> 审查范围：全项目代码与文档

---

## 一、严重 Bug（会导致崩溃或错误行为）

### C1. 缠论段和中枢代码永远不会执行
- **文件**: `backend/app/core/chan_algorithm.py` 第 457-461 行
- **问题**: `calculate_chan_data()` 在第 457 行提前 `return`，只返回 `chan_klines`、`fractals`、`pens`，第 464-474 行的段生成和中枢识别代码永远不会被执行
- **影响**: 缠论分析 API 永远不返回段和中枢数据；前端统计面板中段数量和中枢数量始终为 0

### C2. `identify_zhongshus()` 访问不存在的字段
- **文件**: `backend/app/core/chan_algorithm.py` 第 401-406 行
- **问题**: `identify_zhongshus()` 访问 `pen.start_price` 和 `pen.end_price`，但 `Pen` 模型（`chan_model.py`）只有 `start_index`、`end_index`、`start_date`、`end_date`、`direction` 字段
- **影响**: 如果中枢识别代码被启用，运行时会抛出 `AttributeError`

### C3. K线接口缺少错误处理
- **文件**: `backend/app/api/stock.py` 第 92-99 行
- **问题**: 当 `get_stock_data_bao()` 返回 `False` 时，只打印日志不返回错误响应，后续代码 `df['date']` 会因对 `False` 取下标而崩溃
- **影响**: 数据获取失败时返回 500 错误而非有意义的错误信息

### C4. 分型标记使用不存在的 `price` 字段
- **文件**: `frontend/src/components/KlineChart.vue` 第 67 行
- **问题**: `topFractals.push([fractal.date, fractal.price])`，但 `Fractal` 模型没有 `price` 字段（只有 `index`、`k_index`、`date`、`type`）
- **影响**: 分型标记的 y 坐标为 `undefined`，顶底分型三角形无法正确显示在图表上

---

## 二、高严重度问题

### H1. SQL 注入风险
- **文件**: `backend/app/service/stock.py` 第 203 行
- **问题**: `query_stock()` 直接执行传入的 SQL 字符串，虽然当前调用处只传入固定字符串，但函数签名接受任意 SQL，未来调用者传入用户输入将导致注入

### H2. 全局可变列表非线程安全
- **文件**: `backend/app/api/stock.py` 第 28-30 行
- **问题**: `LIST_STOCKS` 是模块级可变列表，通过 `global` 关键字在异步处理函数中修改，并发请求下可能出现竞态条件

### H3. MySQL 客户端模块级实例化
- **文件**: `backend/app/utils/middleware.py` 第 75 行
- **问题**: `Mysql_client = MysqlClient()` 在模块导入时立即执行，此时配置可能尚未加载，MySQL 可能不可用，导致应用启动失败

### H4. `init()` 未在 uvicorn 启动时执行
- **文件**: `backend/app/main.py` 第 49-58 行
- **问题**: `init()` 函数仅在 `__main__` 块中调用，但 `run.py` 通过 `uvicorn.run("app.main:app", ...)` 导入模块时不执行 `__main__`，导致 Redis/MySQL 客户端初始化依赖模块级实例化

### H5. 30F 周期时间计算错误
- **文件**: `backend/app/service/stock.py` 第 98 行
- **问题**: 30分钟K线的 `start_time` 使用 `timedelta(hours=1)` 计算，应为 `timedelta(minutes=30)`

---

## 三、中等严重度问题

### M1. 生产代码中残留大量 debug print 语句
- `chan_algorithm.py`: 第 83、120、137、183、250、315、448-450 行
- `stock.py`（service）: 第 41-42、47-48、69-70、89-90、95、135、137 行
- `stock.py`（API）: 第 90、93、95 行
- 应替换为 proper logging

### M2. 周期字符串不一致
- 后端 kline 端点默认: `"daily"`
- 后端 chan 端点默认: `"D"`
- 前端发送: `"daily"`、`"60F"`、`"30F"`
- baostock 服务映射: `"daily"`/`"day"`/`"d"` → `"d"`
- 虽然目前可工作但非常脆弱

### M3. `MOCK_STOCKS` 列表已定义但从未使用
- **文件**: `backend/app/api/stock.py` 第 15-26 行
- 死代码，应删除

### M4. `generate_pens()` 函数从未调用
- **文件**: `backend/app/core/chan_algorithm.py` 第 148-207 行
- 实际调用的是 `generate_new_pens()`，`generate_pens()` 是死代码

### M5. `update_all_stock()` 硬编码日期
- **文件**: `backend/app/service/stock.py` 第 170 行
- 默认参数 `"2026-02-27"` 应改为当日日期

### M6. API 默认 end_date 硬编码
- `backend/app/api/stock.py` 第 84-85 行
- `backend/app/api/chan.py` 第 18-19 行
- 默认 `end_date` 为 `"2026-02-26"`，将随时间过时

### M7. 中枢可视化索引错误
- **文件**: `frontend/src/components/KlineChart.vue` 第 77-79 行
- `zs.start_index`/`zs.end_index` 是笔索引而非原始K线索引，用 `props.klineData[zs.start_index]` 取值位置会错误

### M8. KlineChart.vue 无用表达式
- **文件**: `frontend/src/components/KlineChart.vue` 第 49 行
- `props.chanData.chan_klines[pen.start_index].start` 读取值后丢弃，无任何效果

### M9. 日期范围时区问题
- **文件**: `frontend/src/views/Home.vue` 第 108-109 行
- 使用 `toISOString()` 返回 UTC 时间，UTC+8 用户在午夜前后可能获得前一天的日期

---

## 四、低严重度问题

### L1. docker-compose.yml 未包含 Redis 服务
- 仅包含 MySQL，Redis 需单独安装但未文档化

### L2. data_process.py 重复导入
- **文件**: `backend/app/service/data_process.py` 第 5 行和第 11 行重复导入 `ABC`、`abstractmethod`

### L3. ~~tushare 依赖未使用~~ — 已修复
- tushare 已从 requirements.txt 中移除

---

## 五、文档与代码不一致汇总

| 文档描述 | 实际情况 | 涉及文件 |
|---------|---------|---------|
| 使用模拟/生成数据 | 实际使用 baostock 真实行情 + MySQL 持久化 | README.md, SETUP.md, IMPLEMENTATION_SUMMARY.md |
| 仅日K周期可用 | 实际支持 daily、60F、30F | SETUP.md |
| 无数据库持久化 | MySQL 已实现 | SETUP.md, IMPLEMENTATION_SUMMARY.md |
| Redis 未实现 | Redis 缓存已实现 | SETUP.md, IMPLEMENTATION_SUMMARY.md |
| 项目结构含 route.py、data_processor.py 等 | 这些文件不存在；实际有 akshare_service.py、data_process.py 等 | README.md |
| 前端含 History.vue、ChanParams.vue、store/ | 这些文件/目录不存在 | README.md |
| K线接口响应示例为"还没想好" | 实际已有完整响应格式 | README.md |
| 依赖版本过时（Pandas 2.1.3、ECharts 5.5.1） | 实际为 Pandas 2.2.3、ECharts 6.0.0 | IMPLEMENTATION_SUMMARY.md |
| 前端 README 为 Vite 默认模板 | 无项目相关内容 | frontend/README.md |
