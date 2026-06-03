# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ChanChart is a stock chart visualization system implementing Chan Theory (缠论) technical analysis. It has a Python/FastAPI backend and a Vue 3 frontend.

## Development Commands

### Backend
```bash
cd backend
conda run -n ws pip install -r requirements.txt   # install deps
conda run -n ws python run.py                       # start server (auto-inits DB tables + stock list)
conda run -n ws mypy .                              # type check (required after changes)
```

Backend runs on `http://localhost:8000`. Requires MySQL (docker-compose up -d) and Redis running first.

### Frontend
```bash
cd frontend
npm install        # install deps
npm run dev        # dev server on :5173
npm run build      # production build
```

Frontend API base URL configured in `frontend/.env.development`.

## Architecture

### Data Flow
User selects stock → frontend calls `/api/chan/analysis` → backend fetches K-line data from baostock (persists to MySQL) → runs Chan algorithm (inclusion processing → fractal identification → pen generation) → returns fractals + pens → ECharts renders.

### Backend Structure
- `app/api/` — FastAPI routes: `stock.py` (search, kline), `chan.py` (analysis)
- `app/core/chan_algorithm.py` — Chan Theory algorithm: inclusion processing, fractal ID, pen/segment/zhongshu generation. Note: `calculate_chan_data()` returns early after pens — segment and zhongshu code (lines ~464-474) is dead code.
- `app/service/stock.py` — baostock data source + MySQL persistence + stock list management. All K-line data comes from baostock via `get_stock_data_bao()`.
- `app/models/` — Pydantic models: `stock_model.py` (KlineData, StockInfo), `chan_model.py` (Fractal, Pen, Segment, ZhongShu, ClassicChanKline)
- `app/config/config.yaml` — MySQL and Redis connection settings
- `app/utils/middleware.py` — Singleton Redis/MySQL clients (instantiated at module import time)
- `app/utils/redis.py` — Cache get/set wrappers
- `run.py` — Startup script: creates DB tables via `init_tables()`, calls `update_all_stock()` to fetch stock list from baostock, then starts uvicorn

### Frontend Structure
- `src/api/` — Axios client wrappers (`request.js`, `stock.js`, `chan.js`)
- `src/components/KlineChart.vue` — ECharts candlestick + Chan overlay (pens as blue lines, fractals as triangles)
- `src/components/StockSelector.vue` — Remote search dropdown
- `src/views/Home.vue` — Main page with controls, chart, stats panel

### Key Design Decisions
- **Dual data path**: `/api/stock/kline` returns raw K-line data from baostock; `/api/chan/analysis` calls kline internally then runs Chan algorithm
- **Period string inconsistency**: Backend kline defaults to `"daily"`, chan defaults to `"D"`, frontend sends `"daily"`/`"60F"`/`"30F"`. The baostock service normalizes these.
- **Global mutable state**: `LIST_STOCKS` in `stock.py` API is a module-level list modified via `global` — not thread-safe
- **Mysql_client module-level init**: `middleware.py` line 75 instantiates MysqlClient at import time, before config may be loaded

## Code Conventions

- **Environment**: Use conda env `ws` for all Python commands (`conda run -n ws <command>`)
- **Type checking**: Run `conda run -n ws mypy .` after code changes. Fix errors by correcting types; do not use `Any` or `# type: ignore` without justification
- **Language**: Code comments and variable names are in English; API responses and UI text are in Chinese
- **Chan Theory terminology**: 笔=pen, 段=segment, 分型=fractal, 中枢=zhongshu, 包含关系=inclusion relationship, 顶分型=top fractal, 底分型=bottom fractal

## Known Issues

See CODE_REVIEW.md for full list. Critical ones to be aware of:
- `calculate_chan_data()` returns early — segment/zhongshu generation is unreachable dead code
- `identify_zhongshus()` accesses `pen.start_price`/`pen.end_price` which don't exist on the Pen model
- Frontend fractal markers use `fractal.price` which doesn't exist on the Fractal model
- `get_kline_data()` in stock.py API crashes when baostock returns False (no error handling)
- 30F period `start_time` uses `timedelta(hours=1)` instead of `timedelta(minutes=30)`
