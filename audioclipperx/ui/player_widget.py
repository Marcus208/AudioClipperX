import os
import re
from typing import Optional

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from audioclipperx.ui.range_slider import RangeSlider


# ── time helpers ─────────────────────────────────────────────────────────

def _ms_to_str(ms: int) -> str:
    s_total = ms // 1000
    ms_part = (ms % 1000) // 100  # one decimal place
    m, s = divmod(s_total, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}.{ms_part}"
    return f"{m}:{s:02d}.{ms_part}"


def _str_to_ms(text: str) -> Optional[int]:
    """Parse user-typed time into milliseconds.
    Accepts: 90  /  90.5  /  1:30  /  1:30.5  /  0:01:30
    Returns None if unparseable.
    """
    text = text.strip()
    m = re.fullmatch(r"(\d+):(\d+):(\d+)(?:\.(\d))?", text)
    if m:
        h, mn, s, d = m.groups()
        return (int(h) * 3600 + int(mn) * 60 + int(s)) * 1000 + int(d or 0) * 100
    m = re.fullmatch(r"(\d+):(\d+)(?:\.(\d))?", text)
    if m:
        mn, s, d = m.groups()
        return (int(mn) * 60 + int(s)) * 1000 + int(d or 0) * 100
    m = re.fullmatch(r"(\d+)(?:\.(\d+))?", text)
    if m:
        sec, dec = m.groups()
        return int(sec) * 1000 + int((dec or "0")[:3].ljust(3, "0"))
    return None


# ── waveform loader (background thread) ──────────────────────────────────

class WaveformLoader(QThread):
    """Reads audio samples in a background thread and emits normalised amplitude data."""

    waveform_ready = Signal(str, list)  # (path, normalised_peaks)

    def __init__(self, path: str, num_points: int = 1000, parent=None):
        super().__init__(parent)
        self._path = path
        self._num_points = num_points

    def run(self) -> None:
        try:
            from pydub import AudioSegment

            # Load and convert to mono for display
            audio = AudioSegment.from_file(self._path).set_channels(1)
            raw = audio.get_array_of_samples()
            n = len(raw)
            if n == 0:
                return

            bucket = max(1, n // self._num_points)
            peaks: list[float] = []
            for i in range(self._num_points):
                s = i * bucket
                e = min(s + bucket, n)
                if s >= n:
                    peaks.append(0.0)
                    continue
                chunk = raw[s:e]
                peaks.append(float(max(abs(int(v)) for v in chunk)))

            mx = max(peaks) or 1.0
            self.waveform_ready.emit(self._path, [v / mx for v in peaks])
        except Exception:
            pass  # Waveform is decorative; silently skip on failure


# ── editable time field ───────────────────────────────────────────────────

class _TimeEdit(QLineEdit):
    """Single-line time editor; emits a validated ms value on commit."""

    committed = Signal(int)

    def __init__(self, placeholder: str, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setFixedWidth(72)
        self.returnPressed.connect(self._commit)
        self.editingFinished.connect(self._commit)

    def set_ms(self, ms: Optional[int], duration: int) -> None:
        if ms is None or ms <= 0:
            self.setText("")
        elif ms >= duration > 0:
            self.setText("")
        else:
            self.setText(_ms_to_str(ms))

    def _commit(self) -> None:
        text = self.text().strip()
        if not text:
            self.committed.emit(0)
            return
        ms = _str_to_ms(text)
        if ms is not None:
            self.clearFocus()
            self.committed.emit(ms)
        else:
            self.setStyleSheet("border: 1px solid red;")
            self.setStyleSheet("")


# ── main widget ───────────────────────────────────────────────────────────

class PlayerWidget(QWidget):
    """Audio player with waveform display, dual clip handles, and draggable position."""

    # Emits (start_ms, end_ms); 0 / duration is the sentinel for "not set"
    range_changed = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_path: Optional[str] = None
        self._waveform_loader: Optional[WaveformLoader] = None
        self._waveform_cache: dict[str, list[float]] = {}
        self._setup_player()
        self._setup_ui()
        self._connect_signals()
        self.setEnabled(False)

    # ── setup ────────────────────────────────────────────────────────────

    def _setup_player(self) -> None:
        self._player = QMediaPlayer()
        self._audio_out = QAudioOutput()
        self._player.setAudioOutput(self._audio_out)
        self._audio_out.setVolume(0.8)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Range slider (waveform + clip handles + position line)
        self.slider = RangeSlider()
        self.slider.setMinimumHeight(60)
        layout.addWidget(self.slider)

        # Playback controls row
        ctrl = QHBoxLayout()
        self._play_btn = QPushButton("\u25b6")
        self._play_btn.setFixedWidth(40)
        self._time_lbl = QLabel("0:00.0 / 0:00.0")
        self._time_lbl.setAlignment(Qt.AlignCenter)
        ctrl.addWidget(self._play_btn)
        ctrl.addWidget(self._time_lbl, 1)
        layout.addLayout(ctrl)

        # Start / End editable fields + mark buttons + reset
        mark = QHBoxLayout()

        mark.addWidget(QLabel("Start:"))
        self._start_edit = _TimeEdit("0:00.0")
        mark.addWidget(self._start_edit)
        self._mark_start_btn = QPushButton("Mark Start")
        mark.addWidget(self._mark_start_btn)

        mark.addStretch()

        self._mark_end_btn = QPushButton("Mark End")
        mark.addWidget(self._mark_end_btn)
        mark.addWidget(QLabel("End:"))
        self._end_edit = _TimeEdit("--")
        mark.addWidget(self._end_edit)

        mark.addSpacing(8)
        self._reset_btn = QPushButton("Reset")
        self._reset_btn.setToolTip("Reset clip range to full file duration")
        mark.addWidget(self._reset_btn)

        layout.addLayout(mark)

    def _connect_signals(self) -> None:
        self._play_btn.clicked.connect(self._toggle_play)
        self._mark_start_btn.clicked.connect(self._mark_start)
        self._mark_end_btn.clicked.connect(self._mark_end)
        self._reset_btn.clicked.connect(self._reset_range)
        self._start_edit.committed.connect(self._on_start_typed)
        self._end_edit.committed.connect(self._on_end_typed)

        # Clip handle signals
        self.slider.range_changed.connect(self._on_slider_range_changed)

        # Position drag signals: pause on drag start, seek on drag move
        self.slider.seek_started.connect(self._on_seek_started)
        self.slider.seek_requested.connect(self._on_seek_requested)

        # Player signals
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_state_changed)

    # ── public API ───────────────────────────────────────────────────────

    def load_file(self, path: str) -> None:
        self._player.stop()
        self._current_path = path
        self._player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
        self.setEnabled(True)
        self._play_btn.setText("\u25b6")

        # Serve from cache if already sampled; otherwise load in background
        if path in self._waveform_cache:
            self.slider.set_waveform(self._waveform_cache[path])
        else:
            self.slider.set_waveform([])
            self._start_waveform_loader(path)

    def restore_range(self, start_ms: Optional[int], end_ms: Optional[int]) -> None:
        """Restore a previously saved clip range once the player knows the duration."""
        duration = self._player.duration()
        if duration <= 0:
            return
        s = start_ms if start_ms is not None else 0
        e = end_ms   if end_ms   is not None else duration
        self.slider.set_range(s, e)
        self._update_edits()

    def evict_waveform(self, path: str) -> None:
        """Release cached waveform data for a file that has been removed from the list."""
        self._waveform_cache.pop(path, None)

    def get_range(self) -> tuple[Optional[int], Optional[int]]:
        duration = self._player.duration()
        s = self.slider.start_ms
        e = self.slider.end_ms
        return (
            s if s > 0          else None,
            e if duration > 0 and e < duration else None,
        )

    # ── waveform loading ─────────────────────────────────────────────────

    def _start_waveform_loader(self, path: str) -> None:
        if self._waveform_loader and self._waveform_loader.isRunning():
            self._waveform_loader.waveform_ready.disconnect()
            self._waveform_loader.quit()

        self._waveform_loader = WaveformLoader(path, num_points=1000, parent=self)
        self._waveform_loader.waveform_ready.connect(self._on_waveform_ready)
        self._waveform_loader.start()

    def _on_waveform_ready(self, path: str, data: list[float]) -> None:
        # Store in cache regardless of current file, then apply if still active
        self._waveform_cache[path] = data
        if path == self._current_path:
            self.slider.set_waveform(data)

    # ── playback slots ───────────────────────────────────────────────────

    def _toggle_play(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()
        else:
            if self._player.position() >= self.slider.end_ms > 0:
                self._player.setPosition(self.slider.start_ms)
            self._player.play()

    def _mark_start(self) -> None:
        pos = self._player.position()
        self.slider.set_range(pos, self.slider.end_ms)
        self._update_edits()
        self._emit_range()

    def _mark_end(self) -> None:
        pos = self._player.position()
        self.slider.set_range(self.slider.start_ms, pos)
        self._update_edits()
        self._emit_range()

    def _reset_range(self) -> None:
        duration = self._player.duration()
        if duration > 0:
            self.slider.set_range(0, duration)
            self._update_edits()
            self._emit_range()

    def _on_start_typed(self, ms: int) -> None:
        duration = self._player.duration()
        ms = max(0, min(ms, duration))
        self.slider.set_range(ms, max(self.slider.end_ms, ms))
        self._update_edits()
        self._emit_range()

    def _on_end_typed(self, ms: int) -> None:
        duration = self._player.duration()
        if ms == 0:
            ms = duration
        ms = max(0, min(ms, duration))
        self.slider.set_range(min(self.slider.start_ms, ms), ms)
        self._update_edits()
        self._emit_range()

    def _on_slider_range_changed(self, _s: int, _e: int) -> None:
        self._update_edits()
        self._emit_range()

    def _on_seek_started(self) -> None:
        """Pause playback when user starts dragging the position indicator."""
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()

    def _on_seek_requested(self, ms: int) -> None:
        """Seek to position while user drags the position indicator."""
        self._player.setPosition(ms)

    def _on_position_changed(self, pos_ms: int) -> None:
        duration = self._player.duration()
        self.slider.set_position(pos_ms)
        self._time_lbl.setText(f"{_ms_to_str(pos_ms)} / {_ms_to_str(duration)}")

        # Auto-pause at clip end and rewind to clip start
        end = self.slider.end_ms
        if (
            end > 0
            and pos_ms >= end
            and self._player.playbackState() == QMediaPlayer.PlayingState
        ):
            self._player.pause()
            self._player.setPosition(self.slider.start_ms)

    def _on_duration_changed(self, duration_ms: int) -> None:
        if duration_ms > 0:
            self.slider.set_duration(duration_ms)
            self._update_edits()

    def _on_state_changed(self, state) -> None:
        self._play_btn.setText(
            "\u23f8" if state == QMediaPlayer.PlayingState else "\u25b6"
        )

    # ── helpers ──────────────────────────────────────────────────────────

    def _emit_range(self) -> None:
        self.range_changed.emit(self.slider.start_ms, self.slider.end_ms)

    def _update_edits(self) -> None:
        duration = self._player.duration()
        self._start_edit.set_ms(self.slider.start_ms, duration)
        self._end_edit.set_ms(self.slider.end_ms, duration)
