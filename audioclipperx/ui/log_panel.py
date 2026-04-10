from datetime import datetime

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QTextEdit, QVBoxLayout, QWidget


class LogPanel(QWidget):
    """Bottom panel: overall progress bar and scrollable processing log."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Progress row
        progress_row = QHBoxLayout()
        self._status_lbl = QLabel("Ready")
        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%v / %m files")
        self._progress_bar.setFixedHeight(18)
        self._progress_bar.hide()
        progress_row.addWidget(self._status_lbl)
        progress_row.addWidget(self._progress_bar, 1)
        layout.addLayout(progress_row)

        # Log text area
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(140)
        self._log.setStyleSheet(
            "QTextEdit {"
            "  background-color: #1e1e1e;"
            "  color: #d4d4d4;"
            "  font-family: Consolas, 'Courier New', monospace;"
            "  font-size: 12px;"
            "}"
        )
        layout.addWidget(self._log)

    # ── public API ───────────────────────────────────────────────────────

    def append(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._log.append(f"[{ts}] {message}")
        self._log.moveCursor(QTextCursor.End)

    def set_progress(self, completed: int, total: int) -> None:
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(completed)
        self._progress_bar.show()
        self._status_lbl.setText(f"Processing: {completed}/{total}")

    def set_ready(self) -> None:
        self._progress_bar.hide()
        self._status_lbl.setText("Ready")

    def set_done(self, success: int, fail: int) -> None:
        self._progress_bar.hide()
        if fail == 0:
            self._status_lbl.setText(f"Done \u2713 \u2014 All {success} file(s) succeeded")
        else:
            self._status_lbl.setText(f"Done \u2014 \u2713 {success} succeeded  \u2717 {fail} failed")

    def clear(self) -> None:
        self._log.clear()
