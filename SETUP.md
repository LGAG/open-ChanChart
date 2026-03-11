# ChanChart Demo Setup Guide

## Overview
This is a working prototype of the ChanChart system - a stock market visualization tool implementing Chan Theory (缠论) technical analysis.

## System Requirements
- Python 3.8+
- Node.js 16+
- npm or yarn

## Installation

### Middleware Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. start docker container
```bash
docker-compose up -d
```

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Create environment file (optional):
```bash
cp .env.example .env
```

4. Start the backend server:
```bash
python run.py
```

The backend API will be available at `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Usage

1. **Select a Stock**: Use the dropdown to search and select a stock (e.g., "600519" for Guizhou Moutai)
2. **Choose Period**: Select the time period (currently only "日K" - Daily K-line is implemented)
3. **Configure Parameters**: Toggle "包含关系处理" (Inclusion Relationship Processing) as needed
4. **Refresh Data**: Click the "刷新数据" button to reload the chart

## Features

### Backend Features
- **Mock Stock Data**: Generates realistic random K-line data for demo purposes
- **Stock Search API**: Search stocks by code or name
- **Chan Theory Algorithm**:
  - Inclusion relationship processing
  - Fractal identification (top/bottom patterns)
  - Pen generation (strokes connecting fractals)
  - Segment generation
  - Zhongshu (central area) identification

### Frontend Features
- **Interactive Chart**: 
  - Zoom and pan with mouse wheel
  - Data zoom slider
  - Hover tooltips with detailed information
- **Chan Theory Visualization**:
  - K-line candlesticks (red for up, green for down)
  - Fractals marked with triangles
  - Pens shown as blue lines
  - Zhongshu areas marked with dashed lines
- **Volume Chart**: Synchronized volume bars below the main chart
- **Statistics Panel**: Shows counts of fractals, pens, segments, and zhongshus

## API Endpoints

### Stock Search
```
GET /api/stock/search?keyword={keyword}&market={market}
```
Search for stocks by code or name.

### K-line Data
```
GET /api/stock/kline?code={code}&market={market}&period={period}
```
Get raw K-line data for a stock.

### Chan Theory Analysis
```
GET /api/chan/analysis?code={code}&market={market}&period={period}&process_include={true|false}
```
Get K-line data with Chan Theory analysis.

## Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework
- **Pydantic**: Data validation
- **Uvicorn**: ASGI server
- **Python**: Core algorithm implementation

### Frontend
- **Vue 3**: Progressive JavaScript framework
- **Vite**: Next-generation build tool
- **Element Plus**: UI component library
- **ECharts**: Powerful charting library
- **Axios**: HTTP client

## Project Structure

```
open-ChanChart/
├── backend/
│   ├── app/
│   │   ├── api/          # API route handlers
│   │   ├── core/         # Chan Theory algorithm
│   │   ├── models/       # Data models
│   │   └── main.py       # FastAPI application
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── api/          # API clients
│   │   ├── components/   # Vue components
│   │   ├── views/        # Page views
│   │   └── main.js       # Application entry
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Notes

### Current Limitations
- Uses mock/generated data instead of real stock data
- Only daily K-line period is fully functional
- Segment generation is simplified
- No database persistence (all data is generated on-demand)
- No authentication/authorization

### Future Enhancements
- Integration with real stock data sources (Tushare/Akshare)
- Redis caching implementation
- MySQL database for stock information
- Support for intraday periods (30F, 5F)
- Enhanced Chan Theory algorithms
- User authentication and preferences
- Historical data view
- More advanced visualization features

## Cross-Platform Compatibility

The current implementation is cross-platform compatible:
- **Backend**: Python-based, runs on Windows, macOS, and Linux
- **Frontend**: Web-based, accessible from any modern browser
- **Dependencies**: All dependencies are cross-platform

For production deployment, ensure proper environment configuration for your target platform.

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (should be 3.8+)
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check if port 8000 is already in use

### Frontend won't start
- Check Node.js version: `node --version` (should be 16+)
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check if port 5173 is already in use

### Chart not loading
- Ensure backend is running and accessible at `http://localhost:8000`
- Check browser console for errors
- Verify CORS settings in backend `.env` file

## License

This is a demo/prototype project. Please check the repository for license information.
