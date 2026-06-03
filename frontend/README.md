# ChanChart 前端

缠论股票图表可视化系统的前端应用，基于 Vue 3 + Vite + ECharts + Element Plus 构建。

## 开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 环境变量

在 `.env.development` 中配置：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VITE_API_BASE_URL` | 后端 API 地址 | `http://localhost:8000` |

## 组件说明

### KlineChart.vue
K线图表核心组件，基于 ECharts 渲染。

**Props：**
| 属性 | 类型 | 说明 |
|------|------|------|
| klineData | Array | K线数据数组 |
| chanData | Object | 缠论数据（chan_klines、fractals、pens、segments、zhongshus） |

### StockSelector.vue
股票搜索选择组件，基于 Element Plus 的远程搜索 Select。

**Events：**
| 事件 | 参数 | 说明 |
|------|------|------|
| change | Stock 对象 | 选中股票后触发 |

## API 客户端

所有 API 请求通过 `src/api/request.js` 中的 Axios 实例发送，自动添加 baseURL 和响应拦截。

| 函数 | 文件 | 说明 |
|------|------|------|
| `searchStocks(keyword, market)` | stock.js | 搜索股票 |
| `getKlineData(params)` | stock.js | 获取K线数据 |
| `getChanAnalysis(params)` | chan.js | 获取缠论分析 |
