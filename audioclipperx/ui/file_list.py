import os
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView, QHeaderView, QMenu, QTableWidget, QTableWidgetItem,
)

from audioclipperx.models import (
    FileEntry, FileParams,
    STATUS_DONE, STATUS_FAILED, STATUS_PENDING, STATUS_PROCESSING,
)

AUDIO_VIDEO_EXT = {
    ".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a", ".wma", ".opus",
    ".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm", ".m4v", ".ts",
}

COL_CHECK = 0
COL_NAME = 1
COL_START = 2
COL_END = 3
COL_DURATION = 4
COL_PARAMS = 5
COL_STATUS = 6

# Text color per status
_STATUS_COLORS = {
    STATUS_PENDING: QColor(160, 160, 160),
    STATUS_PROCESSING: QColor(240, 190, 50),
    STATUS_DONE: QColor(80, 200, 100),
    STATUS_FAILED: QColor(220, 80, 80),
}


def _ms_to_display(ms: Optional[int]) -> str:
    if ms is None:
        return ""
    s_total = ms / 1000
    m = int(s_total) // 60
    s = s_total - m * 60
    return f"{m}:{s:05.2f}"


class FileListWidget(QTableWidget):
    file_selected = Signal(str)  # emitted with input_path when a row is clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.entries: list[FileEntry] = []
        self._updating = False
        self._setup_ui()
        self.setAcceptDrops(True)

    # ── setup ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels(
            ["", "Filename", "Start", "End", "Duration", "Params", "Status"]
        )
        hdr = self.horizontalHeader()
        hdr.setSectionResizeMode(COL_CHECK, QHeaderView.Fixed)
        hdr.setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        for col in (COL_START, COL_END, COL_DURATION, COL_PARAMS, COL_STATUS):
            hdr.setSectionResizeMode(col, QHeaderView.Fixed)

        self.setColumnWidth(COL_CHECK, 28)
        self.setColumnWidth(COL_START, 78)
        self.setColumnWidth(COL_END, 78)
        self.setColumnWidth(COL_DURATION, 72)
        self.setColumnWidth(COL_PARAMS, 62)
        self.setColumnWidth(COL_STATUS, 78)

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self.cellClicked.connect(self._on_cell_clicked)
        self.itemChanged.connect(self._on_item_changed)

    # ── public API ───────────────────────────────────────────────────────

    def add_files(self, paths: list[str]) -> None:
        existing = {e.input_path for e in self.entries}
        for path in paths:
            if path not in existing and os.path.splitext(path)[1].lower() in AUDIO_VIDEO_EXT:
                self.entries.append(FileEntry(input_path=path))
                existing.add(path)
        self._refresh()

    def update_range(self, input_path: str, start_ms: Optional[int], end_ms: Optional[int]) -> None:
        for i, entry in enumerate(self.entries):
            if entry.input_path == input_path:
                entry.start_ms = start_ms
                entry.end_ms = end_ms
                self._update_row(i, entry)
                break

    def update_status(self, input_path: str, status: str, error: str = "") -> None:
        for i, entry in enumerate(self.entries):
            if entry.input_path == input_path:
                entry.status = status
                entry.error = error
                self._update_row(i, entry)
                break

    def reset_statuses(self) -> None:
        for entry in self.entries:
            entry.status = STATUS_PENDING
            entry.error = ""
        self._refresh()

    def get_enabled_entries(self) -> list[FileEntry]:
        return [e for e in self.entries if e.enabled]

    def set_all_enabled(self, enabled: bool) -> None:
        for entry in self.entries:
            entry.enabled = enabled
        self._refresh()

    # ── internals ────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        self._updating = True
        self.setRowCount(len(self.entries))
        for row, entry in enumerate(self.entries):
            self._update_row(row, entry)
        self._updating = False

    def _update_row(self, row: int, entry: FileEntry) -> None:
        self._updating = True

        # Checkbox
        check = QTableWidgetItem()
        check.setCheckState(Qt.Checked if entry.enabled else Qt.Unchecked)
        check.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        self.setItem(row, COL_CHECK, check)

        # Filename — full path shown in tooltip
        name_item = QTableWidgetItem(entry.filename)
        name_item.setToolTip(entry.input_path)
        self.setItem(row, COL_NAME, name_item)

        # Start / End timestamps
        self.setItem(row, COL_START, QTableWidgetItem(_ms_to_display(entry.start_ms)))
        self.setItem(row, COL_END, QTableWidgetItem(_ms_to_display(entry.end_ms)))

        # Duration (only shown when both endpoints are set)
        if entry.start_ms is not None and entry.end_ms is not None:
            dur_str = f"{(entry.end_ms - entry.start_ms) / 1000:.2f}s"
        else:
            dur_str = ""
        self.setItem(row, COL_DURATION, QTableWidgetItem(dur_str))

        # Params: Global or Custom (blue when custom)
        params_item = QTableWidgetItem("Custom" if entry.has_custom_params() else "Global")
        if entry.has_custom_params():
            params_item.setForeground(QColor(80, 140, 230))
        self.setItem(row, COL_PARAMS, params_item)

        # Status with color coding
        status_item = QTableWidgetItem(entry.status)
        if entry.status in _STATUS_COLORS:
            status_item.setForeground(_STATUS_COLORS[entry.status])
        if entry.error:
            status_item.setToolTip(entry.error)
        self.setItem(row, COL_STATUS, status_item)

        self._updating = False

    def _on_cell_clicked(self, row: int, col: int) -> None:
        if col != COL_CHECK and 0 <= row < len(self.entries):
            self.file_selected.emit(self.entries[row].input_path)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        # Only react to checkbox column changes
        if self._updating or item.column() != COL_CHECK:
            return
        row = item.row()
        if 0 <= row < len(self.entries):
            self.entries[row].enabled = item.checkState() == Qt.Checked

    # ── context menu ─────────────────────────────────────────────────────

    def _context_menu(self, pos) -> None:
        row = self.rowAt(pos.y())
        if row < 0:
            return

        menu = QMenu(self)
        act_remove = menu.addAction("Remove from List")
        menu.addSeparator()
        act_edit = menu.addAction("Edit Parameters...")
        act_reset = menu.addAction("Reset to Global Defaults")
        menu.addSeparator()
        act_all = menu.addAction("Select All")
        act_none = menu.addAction("Deselect All")

        action = menu.exec(self.mapToGlobal(pos))

        if action == act_remove:
            # Remove from list only — the file on disk is never touched
            self.entries.pop(row)
            self._refresh()
        elif action == act_edit:
            self._edit_params(row)
        elif action == act_reset:
            self.entries[row].custom_params = None
            self._update_row(row, self.entries[row])
        elif action == act_all:
            self.set_all_enabled(True)
        elif action == act_none:
            self.set_all_enabled(False)

    def _edit_params(self, row: int) -> None:
        from audioclipperx.ui.params_dialog import FileParamsDialog

        entry = self.entries[row]
        global_params = self.window().settings_panel.get_params()
        current = entry.custom_params if entry.has_custom_params() else global_params

        dlg = FileParamsDialog(
            filename=entry.filename,
            current_params=current,
            global_params=global_params,
            has_custom=entry.has_custom_params(),
            parent=self,
        )
        if dlg.exec():
            has_custom, params = dlg.result_params()
            entry.custom_params = params if has_custom else None
            self._update_row(row, entry)

    # ── drag-and-drop ────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        self.add_files(paths)
