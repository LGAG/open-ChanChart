# ChanChart 安装与使用指南

## 系统要求

- Python 3.8+
- Node.js 16+
- MySQL 8.0+
- Redis 7.0+

## 安装步骤

### 1. 启动 MySQL

使用 Docker Compose 启动 MySQL：

```bash
cd backend
docker-compose up -d
```

这将启动 MySQL 8.0 容器，配置如下：
- 端口：3306
- root 密码：root
- 默认数据库：chan

> **注意**：`docker-compose.yml` 仅包含 MySQL，Redis 需要单独安装。

### 2. 安装 Redis

根据操作系统选择安装方式：

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt update && sudo apt install redis-server
sudo systemctl start redis-server

# Windows (WSL)
sudo apt update && sudo apt install redis-server
sudo systemctl start redis-server

# 验证 Redis 是否运行
redis-cli ping
# 应返回 PONG
```

### 3. 配置后端

#### 3.1 安装 Python 依赖

```bash
cd backend
pip install -r requirements.txt
```

#### 3.2 配置数据库和 Redis

编辑 `app/config/config.yaml`，修改 MySQL 和 Redis 连接信息：

```yaml
redis:
  url: redis://localhost:6379
  host: localhost
  port: 6379
  password: your_redis_pwd   # 如无密码可留空
  db: 0

mysql:
  host: localhost
  port: 3306
  user: root
  password: root
  database: chan
```

#### 3.3 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```
# API 配置
API_HOST=0.0.0.0
API_PORT=8000

# CORS 配置
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

#### 3.4 启动后端

```bash
python run.py
```

首次启动时，`run.py` 会自动：
1. 初始化数据库连接
2. 创建所需的数据表（day、hour、half、week、month、year、stock）
3. 从 baostock 拉取股票列表并写入数据库

后端 API 运行在 `http://localhost:8000`：
- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端运行在 `http://localhost:5173`。

如需修改后端 API 地址，编辑 `frontend/.env.development`：

```
VITE_API_BASE_URL=http://localhost:8000
```

## 使用方法

1. **选择股票**：在搜索框中输入股票代码或名称（如 "600519" 或 "茅台"）
2. **选择周期**：支持日K（daily）、1小时（60F）、30分钟（30F）
3. **选择时间范围**：使用日期选择器指定起止日期
4. **配置参数**：开关"包含关系处理"（默认开启）
5. **刷新数据**：点击"刷新数据"按钮加载图表

## 功能说明

### 后端功能
- **K线数据获取**：通过 baostock 获取真实A股行情数据，自动持久化到 MySQL
- **批量数据更新**：支持按股票代码、周期列表、日期范围组合条件批量更新K线数据
- **股票搜索**：基于 MySQL 数据库的模糊搜索，支持代码/名称匹配
- **缠论算法**：
  - 包含关系处理
  - 顶底分型识别
  - 笔生成（含缺口笔判断）
  - 段生成（已实现，未启用）
  - 中枢识别（已实现，未启用）
- **数据缓存**：Redis 缓存 K 线数据，默认 2 天过期

### 前端功能
- **K线图表**：基于 ECharts 的交互式K线图，支持滚轮缩放、拖拽平移
- **缠论可视化**：
  - K线蜡烛图（红涨绿跌）
  - 顶底分型三角标记
  - 笔线段（蓝色连线）
  - 中枢区域（虚线标记，待启用）
- **成交量图**：主图下方同步显示成交量
- **统计面板**：展示分型、笔、段、中枢数量

## API 接口

### 股票搜索
```
GET /api/stock/search?keyword={keyword}&market={market}
```

### 股票列表
```
POST /api/stock/list
```

### K线数据
```
GET /api/stock/kline?code={code}&market={market}&period={period}&start_date={date}&end_date={date}
```

### 数据更新
```
POST /api/stock/update?code={code}&market={market}&periods={periods}&start_date={date}&end_date={date}
```
- `code`：可选，不填则更新所有股票
- `periods`：可选，逗号分隔的周期列表（day,60F,30F,5F,week,month,year），不填则更新所有周期
- `start_date`/`end_date`：可选日期范围

### 缠论分析
```
GET /api/chan/analysis?code={code}&market={market}&period={period}&process_include={bool}&start_date={date}&end_date={date}
```

## 数据流

```
用户选择股票 → 前端请求 /api/chan/analysis
  → 后端调用 baostock 获取 K 线数据（优先从 Redis 缓存读取）
  → K 线数据写入 MySQL 持久化
  → 执行缠论算法（包含关系处理 → 分型识别 → 笔生成）
  → 返回分型 + 笔数据
  → 前端 ECharts 渲染
```

## 技术栈

### 后端
- **FastAPI**：Web 框架
- **baostock**：K线数据源（日线、60分钟、30分钟、5分钟、周线、月线、年线）+ 股票列表
- **MySQL**：数据持久化（SQLAlchemy + PyMySQL + DBUtils 连接池）
- **Redis**：数据缓存
- **Pydantic**：数据校验

### 前端
- **Vue 3**：UI 框架
- **Vite**：构建工具
- **Element Plus**：UI 组件库
- **ECharts**：图表渲染
- **Axios**：HTTP 客户端

## 故障排除

### MySQL 连接失败
- 确认 MySQL 容器已启动：`docker ps`
- 检查 `config.yaml` 中的连接信息是否正确
- 确认数据库 `chan` 已创建

### Redis 连接失败
- 确认 Redis 服务已启动：`redis-cli ping`
- 检查 `config.yaml` 中的 Redis 配置
- 如无密码，将 `password` 设为 `null`

### 后端启动失败
- 检查 Python 版本：`python --version`（需 3.8+）
- 确认依赖已安装：`pip install -r requirements.txt`
- 检查端口 8000 是否被占用

### 前端启动失败
- 检查 Node.js 版本：`node --version`（需 16+）
- 清除缓存重装：`rm -rf node_modules && npm install`
- 检查端口 5173 是否被占用

### 图表不显示
- 确认后端已启动且可访问 `http://localhost:8000/health`
- 检查浏览器控制台错误信息
- 确认 `.env.development` 中的 API 地址正确

### 股票搜索无结果
- 确认 `run.py` 首次启动已成功拉取股票列表（查看控制台日志）
- 手动触发股票列表更新：调用 `update_all_stock()` 函数
