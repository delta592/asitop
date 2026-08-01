"""Smoke tests for the built-in terminal UI widgets."""

from __future__ import annotations

from collections import deque
from io import StringIO
from unittest.mock import patch

from asitop.tui import HChart, HGauge, HSplit, VGauge, VSplit


class TestTuiWidgets:
    def test_hgauge_value_and_title(self) -> None:
        gauge = HGauge(title="CPU", val=0, color=2)
        gauge.value = 42
        gauge.title = "CPU: 42%"

        assert gauge.value == 42
        assert gauge.title == "CPU: 42%"

    def test_vgauge_accepts_int_value(self) -> None:
        gauge = VGauge(val=0, color=2, border_color=2)
        gauge.value = 75

        assert gauge.value == 75

    def test_hchart_append_and_datapoints_maxlen(self) -> None:
        chart = HChart(title="Power", color=2, val=0)
        chart.datapoints = deque(chart.datapoints, maxlen=3)

        for value in (10, 20, 30, 40):
            chart.append(float(value))

        assert list(chart.datapoints) == [20.0, 30.0, 40.0]

    def test_split_items_accessible(self) -> None:
        left = HGauge(title="Left", val=10, color=2)
        right = HGauge(title="Right", val=20, color=2)
        ui = HSplit(left, right)

        assert ui.items[0] is left
        assert ui.items[1] is right

    def test_display_renders_without_error(self) -> None:
        ui = VSplit(
            HSplit(HGauge(title="CPU", val=50, color=2), HGauge(title="GPU", val=25, color=2)),
            HChart(title="Power", color=2, val=0),
            title="asitop",
            border_color=2,
        )
        ui.items[1].append(33.0)

        with patch("sys.stdout", new_callable=StringIO):
            ui.display()
