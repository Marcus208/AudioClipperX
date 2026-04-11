"""
Range slider with waveform background, dual clip handles, and a draggable position indicator.

Layout (centre cross-section):
  ──────[●══waveform══●]──────────────
          ↑            ↑
        start         end
              |
           position (red, draggable)
"""
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget

HANDLE_R   = 7    # clip handle draw radius
HANDLE_HIT = 12   # clip handle hit radius
POS_HIT    = 8    # position line hit radius
TRACK_H    = 4
MARGIN     = HANDLE_R + 2


class RangeSlider(QWidget):
    range_changed   = Signal(int, int)  # start_ms, end_ms  (clip handles moved)
    seek_started    = Signal()          # position drag began
    seek_requested  = Signal(int)       # position drag in progress, carries ms

    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration: int = 0
        self._start:    int = 0
        self._end:      int = 0
        self._position: int = 0
        self._waveform: list[float] = []  # normalised 0-1 amplitude per display column

        # 'start' | 'end' | 'position' | None
        self._dragging: str | None = None

        self.setMinimumHeight(HANDLE_R * 2 + 16)

    # ── public API ───────────────────────────────────────────────────────

    def set_duration(self, duration_ms: int) -> None:
        self._duration = max(duration_ms, 1)
        self._start    = 0
        self._end      = self._duration
        self._position = 0
        self.update()

    def set_position(self, position_ms: int) -> None:
        self._position = max(0, min(position_ms, self._duration))
        self.update()

    def set_range(self, start_ms: int, end_ms: int) -> None:
        self._start = max(0, min(start_ms, self._duration))
        self._end   = max(0, min(end_ms,   self._duration))
        if self._start > self._end:
            self._start, self._end = self._end, self._start
        self.update()

    def set_waveform(self, data: list[float]) -> None:
        """Accept a list of normalised (0-1) amplitude values."""
        self._waveform = data
        self.update()

    @property
    def start_ms(self) -> int:
        return self._start

    @property
    def end_ms(self) -> int:
        return self._end

    # ── coordinate helpers ───────────────────────────────────────────────

    def _tl(self) -> int:
        return MARGIN

    def _tr(self) -> int:
        return self.width() - MARGIN

    def _tw(self) -> int:
        return max(self._tr() - self._tl(), 1)

    def _cy(self) -> int:
        return self.height() // 2

    def _ms_to_x(self, ms: int) -> int:
        if self._duration == 0:
            return self._tl()
        return self._tl() + int(ms / self._duration * self._tw())

    def _x_to_ms(self, x: int) -> int:
        ratio = (x - self._tl()) / self._tw()
        return int(max(0.0, min(1.0, ratio)) * self._duration)

    # ── painting ─────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cy = self._cy()
        tl = self._tl()
        tw = self._tw()

        # 1. Background track
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(60, 60, 60))
        p.drawRoundedRect(tl, cy - TRACK_H // 2, tw, TRACK_H, 2, 2)

        # 2. Waveform (drawn within the track area, centred vertically)
        if self._waveform:
            n   = len(self._waveform)
            max_h = max(4, (self.height() - 8) // 2)
            p.setPen(QPen(QColor(90, 90, 90), 1))
            for i, amp in enumerate(self._waveform):
                x = tl + int(i / n * tw)
                h = max(1, int(amp * max_h))
                p.drawLine(x, cy - h, x, cy + h)

        # 3. Selected range highlight (over waveform)
        if self._duration > 0:
            sx = self._ms_to_x(self._start)
            ex = self._ms_to_x(self._end)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(60, 120, 210, 120))
            p.drawRect(sx, cy - TRACK_H // 2, ex - sx, TRACK_H)

        # 4. Start handle
        sx = self._ms_to_x(self._start)
        p.setBrush(QColor(80, 140, 230))
        p.setPen(QPen(QColor(200, 220, 255), 2))
        p.drawEllipse(QPoint(sx, cy), HANDLE_R, HANDLE_R)

        # 5. End handle
        ex = self._ms_to_x(self._end)
        p.setBrush(QColor(80, 140, 230))
        p.setPen(QPen(QColor(200, 220, 255), 2))
        p.drawEllipse(QPoint(ex, cy), HANDLE_R, HANDLE_R)

        # 6. Playback position (red, draggable)
        if self._duration > 0:
            px = self._ms_to_x(self._position)
            p.setPen(QPen(QColor(240, 70, 70), 2))
            p.drawLine(px, 2, px, self.height() - 2)
            # Small triangle at top to make it easier to grab
            p.setBrush(QColor(240, 70, 70))
            p.setPen(Qt.NoPen)
            p.drawPolygon([
                QPoint(px - 5, 2),
                QPoint(px + 5, 2),
                QPoint(px, 10),
            ])

    # ── mouse interaction ────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        x = int(event.position().x())

        dist_pos = abs(x - self._ms_to_x(self._position))
        dist_s   = abs(x - self._ms_to_x(self._start))
        dist_e   = abs(x - self._ms_to_x(self._end))

        # Position indicator takes highest priority
        if dist_pos <= POS_HIT:
            self._dragging = "position"
            self.seek_started.emit()
            return

        # Clip handles
        if dist_s <= HANDLE_HIT and dist_e <= HANDLE_HIT:
            # Handles overlap: click right → grab end, click left → grab start
            self._dragging = "end" if x >= self._ms_to_x(self._start) else "start"
        elif dist_s <= HANDLE_HIT:
            self._dragging = "start"
        elif dist_e <= HANDLE_HIT:
            self._dragging = "end"

    def mouseMoveEvent(self, event) -> None:
        if self._dragging is None:
            return
        ms = self._x_to_ms(int(event.position().x()))
        min_gap = max(1, self._duration // 1000)

        if self._dragging == "position":
            self._position = max(0, min(ms, self._duration))
            self.update()
            self.seek_requested.emit(self._position)
        elif self._dragging == "start":
            self._start = max(0, min(ms, self._end - min_gap))
            self.update()
            self.range_changed.emit(self._start, self._end)
        elif self._dragging == "end":
            self._end = min(self._duration, max(ms, self._start + min_gap))
            self.update()
            self.range_changed.emit(self._start, self._end)

    def mouseReleaseEvent(self, _event) -> None:
        self._dragging = None
