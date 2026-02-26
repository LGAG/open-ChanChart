"""Unit tests for the Pydantic models in app.models."""
import pytest
from pydantic import ValidationError

from app.models.stock_model import KlineData, StockInfo, KlineRequest
from app.models.chan_model import Fractal, Pen, Segment, ZhongShu, ChanData


# ---------------------------------------------------------------------------
# KlineData
# ---------------------------------------------------------------------------

class TestKlineData:
    def test_valid_kline(self):
        k = KlineData(date="2024-01-01", open=100.0, high=110.0, low=95.0, close=105.0, volume=50000)
        assert k.date == "2024-01-01"
        assert k.high == 110.0

    def test_missing_required_field_raises_error(self):
        with pytest.raises(ValidationError):
            KlineData(open=100.0, high=110.0, low=95.0, close=105.0, volume=50000)

    def test_invalid_type_raises_error(self):
        with pytest.raises(ValidationError):
            KlineData(date="2024-01-01", open="bad", high=110.0, low=95.0, close=105.0, volume=50000)


# ---------------------------------------------------------------------------
# StockInfo
# ---------------------------------------------------------------------------

class TestStockInfo:
    def test_valid_stock_info(self):
        s = StockInfo(code="000001", name="平安银行", market="sz")
        assert s.code == "000001"
        assert s.market == "sz"

    def test_missing_name_raises_error(self):
        with pytest.raises(ValidationError):
            StockInfo(code="000001", market="sz")


# ---------------------------------------------------------------------------
# KlineRequest
# ---------------------------------------------------------------------------

class TestKlineRequest:
    def test_defaults_are_applied(self):
        req = KlineRequest(code="000001")
        assert req.market == "sh"
        assert req.period == "D"
        assert req.start_date is None
        assert req.end_date is None

    def test_custom_values_are_stored(self):
        req = KlineRequest(code="600519", market="sh", period="30F",
                           start_date="2024-01-01", end_date="2024-12-31")
        assert req.period == "30F"
        assert req.start_date == "2024-01-01"


# ---------------------------------------------------------------------------
# Fractal
# ---------------------------------------------------------------------------

class TestFractal:
    def test_valid_top_fractal(self):
        f = Fractal(index=5, date="2024-01-06", price=115.0, type="top")
        assert f.type == "top"

    def test_valid_bottom_fractal(self):
        f = Fractal(index=3, date="2024-01-04", price=88.0, type="bottom")
        assert f.type == "bottom"

    def test_missing_field_raises_error(self):
        with pytest.raises(ValidationError):
            Fractal(index=1, price=100.0, type="top")


# ---------------------------------------------------------------------------
# Pen
# ---------------------------------------------------------------------------

class TestPen:
    def _pen(self, direction="up"):
        return Pen(
            start_index=1, end_index=5,
            start_date="2024-01-02", end_date="2024-01-06",
            start_price=90.0, end_price=110.0,
            direction=direction,
        )

    def test_valid_up_pen(self):
        pen = self._pen("up")
        assert pen.direction == "up"

    def test_valid_down_pen(self):
        pen = self._pen("down")
        assert pen.direction == "down"

    def test_missing_direction_raises_error(self):
        with pytest.raises(ValidationError):
            Pen(start_index=1, end_index=5,
                start_date="2024-01-02", end_date="2024-01-06",
                start_price=90.0, end_price=110.0)


# ---------------------------------------------------------------------------
# Segment
# ---------------------------------------------------------------------------

class TestSegment:
    def _make_pen(self, direction="up"):
        return Pen(
            start_index=0, end_index=2,
            start_date="2024-01-01", end_date="2024-01-03",
            start_price=90.0, end_price=110.0,
            direction=direction,
        )

    def test_valid_segment(self):
        pens = [self._make_pen("up")] * 3
        seg = Segment(start_index=0, end_index=2, pens=pens, direction="up")
        assert len(seg.pens) == 3

    def test_empty_pens_list_is_allowed(self):
        seg = Segment(start_index=0, end_index=0, pens=[], direction="down")
        assert seg.pens == []


# ---------------------------------------------------------------------------
# ZhongShu
# ---------------------------------------------------------------------------

class TestZhongShu:
    def test_valid_zhongshu(self):
        z = ZhongShu(start_index=0, end_index=6, high=110.0, low=90.0, level=1)
        assert z.high > z.low

    def test_missing_level_raises_error(self):
        with pytest.raises(ValidationError):
            ZhongShu(start_index=0, end_index=6, high=110.0, low=90.0)


# ---------------------------------------------------------------------------
# ChanData
# ---------------------------------------------------------------------------

class TestChanData:
    def test_default_empty_lists(self):
        cd = ChanData()
        assert cd.fractals == []
        assert cd.pens == []
        assert cd.segments == []
        assert cd.zhongshus == []
