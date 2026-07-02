# ChanChart - 缠论股票图表可视化系统

[![Demo Status](https://img.shields.io/badge/demo-working-brightgreen.svg)](https://github.com/LGAG/open-ChanChart)

## 项目简介

ChanChart 是一个基于缠论（缠中说禅理论）的股票K线图表可视化系统，支持K线展示、顶底分型识别、笔生成、段划分和中枢识别等缠论核心结构的可视化。

![主界面](https://github.com/user-attachments/assets/74e2a9c8-7a79-4230-83da-2a3ec5243f7d)
![缠论可视化](https://github.com/user-attachments/assets/498a3acd-32b0-4cb1-9729-a28d742203a1)

## 快速开始

详细安装说明请参考 [SETUP.md](SETUP.md)。

```bash
# 1. 启动中间件（MySQL）
cd backend
docker-compose up -d

# 2. 安装 Redis（如未安装）
# macOS: brew install redis && brew services start redis
# Ubuntu: sudo apt install redis-server && sudo systemctl start redis

# 3. 配置后端
cd backend
cp .env.example .env          # 编辑 API 配置
cp app/config/config.yaml.example app/config/config.yaml  # 编辑数据库/Redis 配置
pip install -r requirements.txt
python run.py                  # 启动后端（自动初始化数据库表）

# 4. 启动前端（另一个终端）
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173 访问应用。

## 技术框架

### 前端
| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.5.25 | UI 框架 |
| Vite | 7.3.1 | 构建工具 |
| Element Plus | 2.13.2 | UI 组件库 |
| ECharts | 6.0.0 | 图表库 |
| Axios | 1.13.5 | HTTP 客户端 |

### 后端
| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.8+ | 核心语言 |
| FastAPI | 0.115.0 | Web 框架 |
| Uvicorn | 0.34.0 | ASGI 服务器 |
| Pydantic | 2.10.5 | 数据校验 |
| Pandas | 2.2.3 | 数据处理 |
| baostock | 0.8.9 | K线数据源 + 股票列表 |
| PyMySQL | 1.1.2 | MySQL 驱动 |
| DBUtils | 3.1.2 | 数据库连接池 |
| SQLAlchemy | - | ORM/数据操作 |
| Redis | 7.x | 数据缓存 |
| PyYAML | - | 配置文件解析 |

### 中间件
| 技术 | 用途 |
|------|------|
| MySQL 8.0 | 数据持久化（K线数据、股票信息） |
| Redis 7.0+ | 缓存（K线数据、搜索结果） |

## 功能需求

### 前端功能
- **K线图表绘制**：支持日K、1小时、30分钟、5分钟、周K、月K、年K等周期K线展示
- **缠论结构可视化**：叠加展示缠论笔（蓝色线段）、顶底分型（红/绿三角标记）
- **股票选择功能**：支持股票代码/名称模糊搜索
- **缠论参数配置**：可配置是否处理包含关系
- **交互功能**：鼠标滚轮缩放K线、悬停显示详情、周期切换、数据刷新
- **时间范围选择**：支持自定义日期范围查询
- **缠论数据统计**：展示分型、笔、段、中枢数量

### 后端功能
- **行情数据接口**：通过 baostock 获取股票K线数据，自动写入 MySQL 持久化
- **批量数据更新**：支持按股票代码、周期列表、日期范围组合条件批量更新K线数据
- **缠论算法实现**：顶底分型识别（处理包含关系）、笔生成（含缺口笔判断）、段生成、中枢识别
- **缠论数据接口**：返回股票对应周期的缠论笔、分型数据
- **股票搜索接口**：基于 MySQL 数据库的模糊搜索，支持按市场过滤
- **数据缓存**：通过 Redis 缓存高频查询的K线数据（默认2小时过期）
- **异常处理**：统一捕获算法计算、接口请求异常

## 项目结构

### 前端
```
frontend/
├── src/
│   ├── api/                    # 接口封装
│   │   ├── request.js          # Axios 实例与拦截器
│   │   ├── stock.js            # 股票搜索、K线接口
│   │   └── chan.js             # 缠论分析接口
│   ├── components/             # 组件
│   │   ├── KlineChart.vue      # K线+缠论图表核心组件
│   │   └── StockSelector.vue   # 股票选择组件
│   ├── views/
│   │   └── Home.vue            # 首页（核心图表展示）
│   ├── App.vue                 # 根组件
│   ├── main.js                 # 入口文件
│   └── style.css               # 全局样式
├── .env.development            # 开发环境配置
├── package.json
├── pnpm-lock.yaml
└── vite.config.js
```

### 后端
```
backend/
├── app/
│   ├── api/                    # 路由层
│   │   ├── stock.py            # 股票搜索、K线、数据更新接口
│   │   └── chan.py             # 缠论分析接口
│   ├── config/                 # 配置
│   │   ├── config.py           # 配置加载（YAML）
│   │   └── config.yaml         # 数据库/Redis 配置
│   ├── core/                   # 核心算法
│   │   └── chan_algorithm.py   # 缠论算法实现
│   ├── models/                 # 数据模型
│   │   ├── db_model.py         # SQLAlchemy ORM 模型（Stock、DayKline 等）
│   │   ├── stock_model.py      # Pydantic 响应模型
│   │   └── chan_model.py       # 缠论数据模型
│   ├── service/                # 服务层
│   │   └── stock.py            # Baostock 数据源 + MySQL 操作
│   ├── utils/                  # 工具
│   │   ├── database.py         # SQLAlchemy 引擎 + Session 管理
│   │   ├── middleware.py       # Redis 单例客户端
│   │   └── redis.py            # Redis 缓存操作
│   └── main.py                 # FastAPI 应用
├── docker-compose.yml          # MySQL 容器配置
├── .env.example                # 环境变量示例
├── requirements.txt            # Python 依赖
└── run.py                      # 启动脚本（含数据库初始化）
```

## API 接口

### 1. 股票搜索
- **请求方式**: GET
- **接口路径**: `/api/stock/search`
- **请求参数**:
  - `keyword`（必填）：股票名称或代码
  - `market`（可选）：市场类型，`sh` 或 `sz`
- **响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": [
    { "code": "000001", "name": "平安银行", "market": "sz" }
  ]
}
```

### 2. 股票列表
- **请求方式**: POST
- **接口路径**: `/api/stock/list`
- **请求参数**: 可选 JSON body
- **响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": [
    { "code": "000001", "name": "平安银行", "market": "sz" }
  ]
}
```

### 3. K线数据
- **请求方式**: GET
- **接口路径**: `/api/stock/kline`
- **请求参数**:
  - `code`（必填）：股票代码
  - `market`（可选，默认 `sh`）：市场类型
  - `period`（可选，默认 `daily`）：周期，可选 `daily`、`60F`、`30F`
  - `start_date`（可选，格式 `YYYY-MM-DD`）：开始日期
  - `end_date`（可选，格式 `YYYY-MM-DD`）：结束日期
- **响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "code": "600519",
    "market": "sh",
    "period": "daily",
    "klines": [
      {
        "date": "2025-01-02",
        "open": 1480.0,
        "high": 1500.0,
        "low": 1475.0,
        "close": 1495.0,
        "volume": 12345,
        "period": "day",
        "level": 6,
        "code": "600519"
      }
    ]
  }
}
```

### 4. 数据更新
- **请求方式**: POST
- **接口路径**: `/api/stock/update`
- **请求参数**:
  - `code`（可选）：股票代码，不填则更新所有股票
  - `market`（可选，默认 `sh`）：市场类型
  - `periods`（可选）：周期列表，逗号分隔，如 `day,60F,30F,5F,week,month,year`，不填则更新所有周期
  - `start_date`（可选，格式 `YYYY-MM-DD`）：开始日期，不填则默认一年前
  - `end_date`（可选，格式 `YYYY-MM-DD`）：结束日期，不填则默认今天
- **支持的周期值**: `day`(日K)、`60F`(1小时)、`30F`(30分钟)、`5F`(5分钟)、`week`(周K)、`month`(月K)、`year`(年K)
- **响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "sh.600519": {
      "日K": "成功(245条)",
      "60分K": "成功(980条)",
      "30分K": "成功(1960条)"
    }
  }
}
```

### 5. 缠论分析
- **请求方式**: GET
- **接口路径**: `/api/chan/analysis`
- **请求参数**:
  - `code`（必填）：股票代码
  - `market`（可选，默认 `sh`）：市场类型
  - `period`（可选，默认 `D`）：周期，可选 `D`、`60F`、`30F`
  - `start_date`（可选，格式 `YYYY-MM-DD`）：开始日期
  - `end_date`（可选，格式 `YYYY-MM-DD`）：结束日期
- **响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "code": "600519",
    "market": "sh",
    "period": "D",
    "klines": [ ... ],
    "chan": {
      "chan_klines": [ ... ],
      "fractals": [
        { "index": 5, "k_index": 5, "date": "2025-01-08", "type": "top" }
      ],
      "pens": [
        { "start_index": 3, "end_index": 8, "start_date": "2025-01-06", "end_date": "2025-01-13", "direction": "up" }
      ]
    }
  }
}
```

> **注意**：段（segments）和中枢（zhongshus）数据当前未在 API 响应中返回，算法已实现但尚未启用。

## 已知问题

详见 [CODE_REVIEW.md](CODE_REVIEW.md)，主要包括：
- 缠论段和中枢计算结果未在 API 中返回
- 前端分型标记因缺少 `price` 字段无法正确显示
- 30分钟K线时间计算有误
- 部分代码存在 SQL 注入风险和线程安全问题
