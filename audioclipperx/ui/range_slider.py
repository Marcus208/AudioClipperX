"""
Custom range slider with two draggable handles and a playback position indicator.

  ─────[●══════════════●]─────────  ← track
        ↑              ↑
      start           end
              |
           position (red line)
"""
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget

HANDLE_R = 7        # handle draw radius
HANDLE_HIT = 12     # hit-test radius (larger for easier grabbing)
TRACK_H = 6
MARGIN = HANDLE_R + 2


class RangeSlider(QWidget):
    range_changed = Signal(int, int)  # start_ms, end_ms

    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration: int = 0
        self._start: int = 0
        self._end: int = 0
        self._position: int = 0
        self._dragging: str | None = None  # 'start' | 'end'
        self.setMinimumHeight(HANDLE_R * 2 + 10)

    # ── public API ──────────────────────────────────────────────────────

    def set_duration(self, duration_ms: int) -> None:
        self._duration = max(duration_ms, 1)
        self._start = 0
        self._end = self._duration
        self._position = 0
        self.update()

    def set_position(self, position_ms: int) -> None:
        self._position = max(0, min(position_ms, self._duration))
        self.update()

    def set_range(self, start_ms: int, end_ms: int) -> None:
        self._start = max(0, min(start_ms, self._duration))
        self._end = max(0, min(end_ms, self._duration))
        if self._start > self._end:
            self._start, self._end = self._end, self._start
        self.update()

    @property
    def start_ms(self) -> int:
        return self._start

    @property
    def end_ms(self) -> int:
        return self._end

    # ── coordinate helpers ───────────────────────────────────────────────

    def _track_left(self) -> int:
        return MARGIN

    def _track_right(self) -> int:
        return self.width() - MARGIN

    def _track_width(self) -> int:
        return max(self._track_right() - self._track_left(), 1)

    def _cy(self) -> int:
        return self.height() // 2

    def _ms_to_x(self, ms: int) -> int:
        if self._duration == 0:
            return self._track_left()
        ratio = ms / self._duration
        return self._track_left() + int(ratio * self._track_width())

    def _x_to_ms(self, x: int) -> int:
        ratio = (x - self._track_left()) / self._track_width()
        ratio = max(0.0, min(1.0, ratio))
        return int(ratio * self._duration)

    # ── painting ─────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cy = self._cy()

        # Background track
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(70, 70, 70))
        p.drawRoundedRect(
            self._track_left(), cy - TRACK_H // 2,
            self._track_width(), TRACK_H, 3, 3,
        )

        # Selected range
        if self._duration > 0:
            sx = self._ms_to_x(self._start)
            ex = self._ms_to_x(self._end)
            p.setBrush(QColor(60, 120, 210))
            p.drawRect(sx, cy - TRACK_H // 2, ex - sx, TRACK_H)

        # Start handle
        sx = self._ms_to_x(self._start)
        p.setBrush(QColor(80, 140, 230))
        p.setPen(QPen(QColor(200, 220, 255), 2))
        p.drawEllipse(QPoint(sx, cy), HANDLE_R, HANDLE_R)

        # End handle
        ex = self._ms_to_x(self._end)
        p.setBrush(QColor(80, 140, 230))
        p.setPen(QPen(QColor(200, 220, 255), 2))
        p.drawEllipse(QPoint(ex, cy), HANDLE_R, HANDLE_R)

        # Playback position line
        if self._duration > 0:
            px = self._ms_to_x(self._position)
            p.setPen(QPen(QColor(240, 80, 80), 2))
            p.drawLine(px, 3, px, self.height() - 3)

    # ── mouse interaction ────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        x = int(event.position().x())
        dist_s = abs(x - self._ms_to_x(self._start))
        dist_e = abs(x - self._ms_to_x(self._end))

        # When both handles overlap exactly, click position decides which to grab:
        # clicking to the right grabs end, to the left grabs start.
        if dist_s <= HANDLE_HIT and dist_e <= HANDLE_HIT:
            mid = self._ms_to_x(self._start)
            self._dragging = "end" if x >= mid else "start"
        elif dist_s <= HANDLE_HIT:
            self._dragging = "start"
        elif dist_e <= HANDLE_HIT:
            self._dragging = "end"

    def mouseMoveEvent(self, event) -> None:
        if self._dragging is None:
            return
        ms = self._x_to_ms(int(event.position().x()))
        min_gap = max(1, self._duration // 1000)  # at least 0.1% gap

        if self._dragging == "start":
            self._start = max(0, min(ms, self._end - min_gap))
        else:
            self._end = min(self._duration, max(ms, self._start + min_gap))

        self.update()
        self.range_changed.emit(self._start, self._end)

    def mouseReleaseEvent(self, _event) -> None:
        self._dragging = None
