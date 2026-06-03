# ChanChart 实现概要

## 项目概述

ChanChart 是一个基于缠论（缠中说禅理论）的股票K线图表可视化系统，采用前后端分离架构，后端提供 K 线数据获取与缠论算法计算，前端负责交互式图表渲染。

## 架构

### 后端（FastAPI + baostock + MySQL + Redis）

```
backend/
├── app/
│   ├── api/                    # API 路由
│   │   ├── stock.py            # 股票搜索 (GET /search)、股票列表 (POST /list)、K线数据 (GET /kline)
│   │   └── chan.py             # 缠论分析 (GET /analysis)
│   ├── config/                 # 配置
│   │   ├── config.py           # YAML 配置加载
│   │   └── config.yaml         # MySQL/Redis 连接配置
│   ├── core/                   # 缠论核心算法
│   │   └── chan_algorithm.py   # 包含关系处理、分型识别、笔生成、段生成、中枢识别
│   ├── models/                 # 数据模型
│   │   ├── db_model.py         # SQLAlchemy ORM 模型（Stock、DayKline、HourKline 等）
│   │   ├── stock_model.py      # Pydantic 响应模型（KlineData、StockInfo）
│   │   └── chan_model.py       # ClassicChanKline、Fractal、Pen、Segment、ZhongShu
│   ├── service/                # 服务层
│   │   └── stock.py            # Baostock 数据源 + MySQL ORM 操作 + 批量数据更新
│   ├── utils/                  # 工具
│   │   ├── database.py         # SQLAlchemy 引擎 + Session 管理
│   │   ├── middleware.py       # RedisClient 单例
│   │   └── redis.py            # 缓存读写封装
│   └── main.py                 # FastAPI 应用入口
├── docker-compose.yml          # MySQL 8.0 容器
├── .env.example                # 环境变量示例
├── requirements.txt            # Python 依赖
└── run.py                      # 启动脚本（初始化数据库+拉取股票列表+启动服务）
```

### 前端（Vue 3 + Vite + ECharts）

```
frontend/
├── src/
│   ├── api/                    # API 客户端
│   │   ├── request.js          # Axios 实例（baseURL、拦截器）
│   │   ├── stock.js            # searchStocks、getKlineData
│   │   └── chan.js             # getChanAnalysis
│   ├── components/             # 组件
│   │   ├── KlineChart.vue      # K线+缠论图表（ECharts）
│   │   └── StockSelector.vue   # 股票搜索选择器
│   ├── views/
│   │   └── Home.vue            # 主页面（控制面板+图表+统计）
│   ├── App.vue
│   ├── main.js
│   └── style.css
├── .env.development            # API 地址配置
├── package.json
├── pnpm-lock.yaml
└── vite.config.js
```

## 缠论算法实现

### 1. 包含关系处理（`process_inclusion`）
- 识别并合并存在包含关系的K线
- 上升趋势取高中高、低中高；下降趋势取低中低、高中低
- 输出经过合并处理的缠论K线序列

### 2. 分型识别（`identify_fractals`）
- 顶分型：中间K线高低点均高于左右两根
- 底分型：中间K线高低点均低于左右两根
- 分型标记包含原始K线索引（`k_index`），用于定位价格

### 3. 笔生成（`generate_new_pens`）
- 连接交替的顶底分型，需满足最小间距（至少4根K线）
- 支持缺口笔：反向跨越缺口也可生成新笔
- 同方向笔延伸：无新反向笔时不另起笔

### 4. 段生成（`generate_segments`）— 已实现但未启用
- 根据笔的方向和高低点关系划分线段
- 当前在 `calculate_chan_data()` 中为死代码

### 5. 中枢识别（`identify_zhongshus`）— 已实现但未启用
- 寻找至少三笔的价格重叠区域
- 当前存在字段访问错误（访问 `pen.start_price`/`end_price`，Pen 模型中不存在）

## 数据源

| 数据 | 来源 | 缓存 |
|------|------|------|
| K线数据（日线/60分/30分） | baostock | MySQL 持久化 |
| 股票列表 | baostock `query_all_stock` | MySQL 持久化 |
| 股票搜索 | MySQL 数据库 | 无 |

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stock/search` | 股票模糊搜索（keyword, market） |
| POST | `/api/stock/list` | 获取完整股票列表 |
| GET | `/api/stock/kline` | K线数据（code, market, period, start_date, end_date） |
| POST | `/api/stock/update` | 批量更新K线数据（code, market, periods, start_date, end_date） |
| GET | `/api/chan/analysis` | 缠论分析（code, market, period, process_include, start_date, end_date） |
| GET | `/health` | 健康检查 |
| GET | `/` | API 信息 |

## 依赖版本

### 后端
| 依赖 | 版本 |
|------|------|
| FastAPI | 0.115.0 |
| Uvicorn | 0.34.0 |
| Pydantic | 2.10.5 |
| Pandas | 2.2.3 |
| baostock | 0.8.9 |
| PyMySQL | 1.1.2 |
| DBUtils | 3.1.2 |
| redis | 7.x |

### 前端
| 依赖 | 版本 |
|------|------|
| Vue | 3.5.25 |
| Vite | 7.3.1 |
| Element Plus | 2.13.2 |
| ECharts | 6.0.0 |
| Axios | 1.13.5 |

## 当前状态

### 已实现
- K线数据获取与持久化（baostock → MySQL，通过 SQLAlchemy ORM）
- 批量数据更新接口（支持按股票/周期/日期范围组合条件）
- 包含关系处理
- 顶底分型识别
- 笔生成（含缺口笔处理）
- 股票模糊搜索
- Redis 缓存
- 前端交互式K线图
- 前端笔线段可视化
- 日K/1小时/30分钟/5分钟/周K/月K/年K周期支持

### 已实现但未启用
- 段生成算法（`generate_segments`）：代码存在于 `chan_algorithm.py`，但在 `calculate_chan_data()` 中因提前 return 而不会执行
- 中枢识别算法（`identify_zhongshus`）：代码存在但同上原因未执行，且存在字段访问错误

### 待完善
- 分型标记价格显示（前端使用不存在的 `fractal.price` 字段）
- 段和中枢的前端可视化
- 5分钟K线周期支持
- 生产级日志替代 print 语句
- 统一的周期字符串格式

## 已知问题

详见 [CODE_REVIEW.md](CODE_REVIEW.md)
