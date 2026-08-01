"""Terminal dashboard widgets for asitop.

Provides the subset of the former ``dashing`` API used by asitop, implemented
with the standard library only so the project no longer depends on the
unmaintained third-party package.
"""

from __future__ import annotations

from collections import deque
import colorsys
import shutil
import sys
from typing import NamedTuple, cast

# Box-drawing and bar characters (same repertoire as dashing)
_BORDER_BL = "└"
_BORDER_BR = "┘"
_BORDER_TL = "┌"
_BORDER_TR = "┐"
_BORDER_H = "─"
_BORDER_V = "│"
_HBAR_ELEMENTS = ("▏", "▎", "▍", "▌", "▋", "▊", "▉")
_VBAR_ELEMENTS = ("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")

_ANSI_PALETTE: tuple[tuple[int, int, int], ...] = (
    (0, 0, 0),
    (255, 0, 0),
    (0, 255, 0),
    (255, 255, 0),
    (0, 0, 255),
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 255),
)


class RGB:
    """An RGB color stored as three integers."""

    __slots__ = ("b", "g", "r")

    def __init__(self, r: int, g: int, b: int) -> None:
        self.r = r
        self.g = g
        self.b = b

    def to_hls(self) -> tuple[float, float, float]:
        return colorsys.rgb_to_hls(self.r / 255.0, self.g / 255.0, self.b / 255.0)

    def escape(self) -> str:
        return f"\033[38;2;{self.r};{self.g};{self.b}m"


Color = int | str | None | RGB


def _init_color(color: Color) -> RGB | None:
    if color is None:
        return None
    if isinstance(color, RGB):
        return color
    if isinstance(color, str):
        if color.startswith("#") and len(color) == 7:
            return RGB(int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))
        msg = f"Invalid color string: {color!r}"
        raise ValueError(msg)
    if 0 <= color < len(_ANSI_PALETTE):
        r, g, b = _ANSI_PALETTE[color]
        return RGB(r, g, b)
    msg = f"ANSI color index out of range: {color}"
    raise ValueError(msg)


def _interpolate_colors(high: RGB, low: RGB, steps: int, pos: int) -> RGB:
    start = colorsys.rgb_to_hsv(low.r / 255.0, low.g / 255.0, low.b / 255.0)
    end = colorsys.rgb_to_hsv(high.r / 255.0, high.g / 255.0, high.b / 255.0)
    k = pos / float(steps)
    h = start[0] + (end[0] - start[0]) * k
    s = start[1] + (end[1] - start[1]) * k
    v = start[2] + (end[2] - start[2]) * k
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return RGB(int(r * 255), int(g * 255), int(b * 255))


class _Terminal:
    def __init__(self) -> None:
        size = shutil.get_terminal_size(fallback=(80, 24))
        self.width = size.columns
        self.height = size.lines

    @staticmethod
    def move(row: int, col: int) -> str:
        return f"\033[{row + 1};{col + 1}H"

    @staticmethod
    def color_rgb(r: int, g: int, b: int) -> str:
        return f"\033[38;2;{r};{g};{b}m"


class TBox(NamedTuple):
    t: _Terminal
    x: int
    y: int
    w: int
    h: int


class _Buf:
    __slots__ = ("_parts",)

    def __init__(self) -> None:
        self._parts: list[str] = []

    def add(self, *parts: str) -> None:
        self._parts.extend(parts)

    def print(self) -> None:
        sys.stdout.write("".join(self._parts))
        sys.stdout.flush()


class Tile:
    """Base class for dashboard tiles."""

    title: str
    items: list[Tile]
    border: bool
    parent: Tile | None
    _terminal: _Terminal | None
    _text_color: RGB | None
    _border_color: RGB | None
    _color_high: RGB | None
    _color_low: RGB | None

    def __init__(
        self,
        title: str = "",
        border: bool = True,
        border_color: Color = None,
        color: Color = None,
        color_high: Color = None,
        color_low: Color = None,
    ) -> None:
        self.title = title
        self._terminal = None
        self.parent = None
        self.items = []
        self.border = border
        self._text_color = _init_color(color)
        self._border_color = _init_color(border_color)
        self._color_high = _init_color(color_high)
        self._color_low = _init_color(color_low)

    def _inherit_color(self, name: str) -> RGB:
        private = f"_{name}"
        value = getattr(self, private)
        if isinstance(value, RGB):
            return value
        if self.parent is not None:
            parent_value = getattr(self.parent, name)
            return cast("RGB", parent_value)
        default = RGB(128, 128, 128)
        setattr(self, private, default)
        return default

    @property
    def text_color(self) -> RGB:
        return self._inherit_color("text_color")

    @property
    def border_color(self) -> RGB:
        return self._inherit_color("border_color")

    @property
    def color_high(self) -> RGB:
        return self._inherit_color("color_high")

    @property
    def color_low(self) -> RGB:
        return self._inherit_color("color_low")

    def _display(self, buf: _Buf, tbox: TBox) -> None:
        raise NotImplementedError

    def _draw_borders_and_title(self, buf: _Buf, tbox: TBox) -> TBox:
        if self.border:
            buf.add(self.border_color.escape())
            for dx in range(1, tbox.h - 1):
                buf.add(tbox.t.move(tbox.x + dx, tbox.y), _BORDER_V)
                buf.add(tbox.t.move(tbox.x + dx, tbox.y + tbox.w - 1), _BORDER_V)
            buf.add(
                tbox.t.move(tbox.x + tbox.h - 1, tbox.y),
                _BORDER_BL,
                _BORDER_H * (tbox.w - 2),
                _BORDER_BR,
            )
            if self.title:
                margin = int((tbox.w - len(self.title)) / 20)
                border_t = _BORDER_H * (margin - 1) + " " * margin + self.title + " " * margin
                border_t += (tbox.w - len(border_t) - 2) * _BORDER_H
            else:
                border_t = _BORDER_H * (tbox.w - 2)
            buf.add(tbox.t.move(tbox.x, tbox.y), _BORDER_TL, border_t, _BORDER_TR)
            return TBox(tbox.t, tbox.x + 1, tbox.y + 1, tbox.w - 2, tbox.h - 2)

        if self.title:
            margin = int((tbox.w - len(self.title)) / 20)
            title = " " * margin + self.title + " " * (tbox.w - margin - len(self.title))
            buf.add(tbox.t.move(tbox.x, tbox.y), title)
            return TBox(tbox.t, tbox.x + 1, tbox.y, tbox.w, tbox.h - 1)

        return tbox

    def _fill_area(self, buf: _Buf, tbox: TBox, char: str) -> None:
        for dx in range(tbox.h):
            buf.add(tbox.t.move(tbox.x + dx, tbox.y), char * tbox.w)

    def display(self, terminal: _Terminal | None = None) -> None:
        if self._terminal is None:
            self._terminal = terminal or _Terminal()
        t = self._terminal
        tbox = TBox(t, 0, 0, t.width, t.height - 1)
        buf = _Buf()
        self._display(buf, tbox)
        buf.add(t.move(t.height - 3, 0), self.border_color.escape())
        buf.print()


class Split(Tile):
    def __init__(self, *items: Tile, border: bool = False, **kwargs: object) -> None:
        kwargs["border"] = border
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.items = list(items)
        self._update_children()

    def _update_children(self) -> None:
        for item in self.items:
            item.parent = self


class VSplit(Split):
    def _display(self, buf: _Buf, tbox: TBox) -> None:
        tbox = self._draw_borders_and_title(buf, tbox)
        if not self.items:
            return

        item_height = tbox.h // len(self.items)
        item_width = tbox.w
        row = tbox.x
        for item in self.items:
            item._display(buf, TBox(tbox.t, row, tbox.y, item_width, item_height))
            row += item_height

        leftover = tbox.h - row + tbox.x
        if leftover > 0:
            self._fill_area(buf, TBox(tbox.t, row, tbox.y, tbox.w, leftover), " ")


class HSplit(Split):
    def _display(self, buf: _Buf, tbox: TBox) -> None:
        tbox = self._draw_borders_and_title(buf, tbox)
        if not self.items:
            return

        item_height = tbox.h
        item_width = tbox.w // len(self.items)
        col = tbox.y
        for item in self.items:
            item._display(buf, TBox(tbox.t, tbox.x, col, item_width, item_height))
            col += item_width

        leftover = tbox.w - col + tbox.y
        if leftover > 0:
            self._fill_area(buf, TBox(tbox.t, tbox.x, col, leftover - 1, tbox.h), " ")


class HGauge(Tile):
    value: int | float
    label: str

    def __init__(
        self,
        label: str = "",
        val: float = 100,
        color: Color = None,
        **kwargs: object,
    ) -> None:
        super().__init__(color=color, **kwargs)  # type: ignore[arg-type]
        self.value = val
        self.label = label

    def _display(self, buf: _Buf, tbox: TBox) -> None:
        tbox = self._draw_borders_and_title(buf, tbox)
        if self.label:
            label_width = len(self.label)
            bar_width = (tbox.w - label_width - 3) * self.value / 100
            center_row = int(tbox.h * 0.5)
            bar_inner_width = int(bar_width)
            filler_width = tbox.w - bar_inner_width - label_width - 2
        else:
            label_width = 0
            bar_width = tbox.w * self.value / 100.0
            center_row = None
            bar_inner_width = int(bar_width)
            filler_width = tbox.w - bar_inner_width - 1

        row_parts: list[str] = []
        total_width = bar_inner_width + filler_width
        for pos in range(bar_inner_width):
            color = _interpolate_colors(self.color_high, self.color_low, total_width, pos)
            row_parts.extend((color.escape(), _HBAR_ELEMENTS[-1]))

        selector = int((bar_width - int(bar_width)) * 7)
        row_parts.extend((
            _HBAR_ELEMENTS[selector],
            self.text_color.escape(),
            _HBAR_ELEMENTS[0] * filler_width,
        ))

        for dx in range(tbox.h):
            move = tbox.t.move(tbox.x + dx, tbox.y)
            if self.label:
                if dx == center_row:
                    buf.add(move, self.label, " ")
                else:
                    buf.add(move, " " * label_width, " ")
            else:
                buf.add(move)
            buf.add(*row_parts)


class VGauge(Tile):
    value: int | float

    def __init__(self, val: float = 100, color: Color = None, **kwargs: object) -> None:
        super().__init__(color=color, **kwargs)  # type: ignore[arg-type]
        self.value = val

    def _display(self, buf: _Buf, tbox: TBox) -> None:
        tbox = self._draw_borders_and_title(buf, tbox)
        filled_height = tbox.h * (self.value / 100.5)
        buf.add(tbox.t.move(tbox.x, tbox.y), self.text_color.escape())
        for dx in range(tbox.h):
            move = tbox.t.move(tbox.x + tbox.h - dx - 1, tbox.y)
            buf.add(move)
            color = _interpolate_colors(self.color_high, self.color_low, tbox.h, dx)
            buf.add(color.escape())
            if dx < int(filled_height):
                buf.add(_VBAR_ELEMENTS[-1] * tbox.w)
            elif dx == int(filled_height):
                index = int((filled_height - int(filled_height)) * 8)
                buf.add(_VBAR_ELEMENTS[index] * tbox.w)
            else:
                buf.add(" " * tbox.w)


class HChart(Tile):
    value: int | float
    datapoints: deque[float]

    def __init__(self, val: float = 100, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.value = val
        self.datapoints = deque(maxlen=500)

    def append(self, dp: float) -> None:
        self.datapoints.append(dp)

    def _chart_char(self, dp: float, row: int, height: int) -> str:
        q = (1 - dp / 100) * height
        if row == int(q):
            index = int((int(q) - q) * 8 - 1)
            return _VBAR_ELEMENTS[index]
        if row < int(q):
            return " "
        return _VBAR_ELEMENTS[-1]

    def _display(self, buf: _Buf, tbox: TBox) -> None:
        tbox = self._draw_borders_and_title(buf, tbox)
        buf.add(self.text_color.escape())
        for dx in range(tbox.h):
            bar = ""
            for dy in range(tbox.w):
                dp_index = -tbox.w + dy
                try:
                    dp = self.datapoints[dp_index]
                except IndexError:
                    bar += " "
                    continue
                bar += self._chart_char(dp, dx, tbox.h)
            buf.add(tbox.t.move(tbox.x + dx, tbox.y), bar)


__all__ = ["HChart", "HGauge", "HSplit", "VGauge", "VSplit"]
