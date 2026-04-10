import os
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPushButton, QSplitter, QTextEdit,
    QVBoxLayout, QWidget,
)

from audioclipperx.models import AudioTask, STATUS_DONE, STATUS_FAILED, STATUS_PROCESSING
from audioclipperx.ui.file_list import AUDIO_VIDEO_EXT, FileListWidget
from audioclipperx.ui.log_panel import LogPanel
from audioclipperx.ui.player_widget import PlayerWidget
from audioclipperx.ui.settings_panel import SettingsPanel
from audioclipperx.worker import ProcessingWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AudioClipperX")
        self.setMinimumSize(960, 680)
        self._current_path: Optional[str] = None
        self._worker: Optional[ProcessingWorker] = None
        self._setup_ui()

    # ── UI construction ──────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Global settings panel
        self.settings_panel = SettingsPanel()
        layout.addWidget(self.settings_panel)

        # Toolbar
        toolbar = QHBoxLayout()
        self._add_btn = QPushButton("+ Add Files")
        self._add_btn.clicked.connect(self._add_files)
        self._add_folder_btn = QPushButton("+ Add Folder")
        self._add_folder_btn.clicked.connect(self._add_folder)
        self._paste_btn = QPushButton("+ Paste Paths")
        self._paste_btn.clicked.connect(self._paste_paths)
        self._paste_btn.setToolTip("Paste file paths manually (one per line) — useful when the file browser cannot list the directory")
        self._sel_all_btn = QPushButton("Select All")
        self._sel_all_btn.clicked.connect(lambda: self.file_list.set_all_enabled(True))
        self._desel_btn = QPushButton("Deselect All")
        self._desel_btn.clicked.connect(lambda: self.file_list.set_all_enabled(False))
        toolbar.addWidget(self._add_btn)
        toolbar.addWidget(self._add_folder_btn)
        toolbar.addWidget(self._paste_btn)
        toolbar.addWidget(self._sel_all_btn)
        toolbar.addWidget(self._desel_btn)
        toolbar.addStretch()
        self._process_btn = QPushButton("Start Processing")
        self._process_btn.setFixedHeight(32)
        self._process_btn.clicked.connect(self._start_processing)
        toolbar.addWidget(self._process_btn)
        layout.addLayout(toolbar)

        # File list + player (horizontal splitter)
        splitter = QSplitter(Qt.Horizontal)

        self.file_list = FileListWidget()
        self.file_list.file_selected.connect(self._on_file_selected)
        splitter.addWidget(self.file_list)

        self.player = PlayerWidget()
        self.player.range_changed.connect(self._on_range_changed)
        self.player._player.durationChanged.connect(self._on_duration_loaded)
        splitter.addWidget(self.player)

        splitter.setSizes([560, 360])
        layout.addWidget(splitter, 1)

        # Log panel
        self.log_panel = LogPanel()
        layout.addWidget(self.log_panel)

    # ── file management ──────────────────────────────────────────────────

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Add Audio / Video Files",
            "",
            "Audio/Video Files (*.mp3 *.wav *.flac *.ogg *.aac *.m4a *.wma "
            "*.mp4 *.mkv *.avi *.mov *.flv *.wmv *.webm *.m4v *.ts)",
        )
        if paths:
            self.file_list.add_files(paths)

    def _paste_paths(self) -> None:
        """Open a text box where users can paste file paths directly (one per line).
        Bypasses the file browser entirely — useful for WSL2 directories with I/O errors.
        """
        dlg = QDialog(self)
        dlg.setWindowTitle("Paste File Paths")
        dlg.setMinimumSize(600, 300)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("Paste file paths below, one per line:"))
        editor = QTextEdit()
        editor.setPlaceholderText("/mnt/e/music/track01.mp3\n/mnt/e/music/track02.mp3")
        layout.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.Accepted:
            return

        raw = editor.toPlainText()
        paths = [p.strip().strip('"').strip("'") for p in raw.splitlines() if p.strip()]
        valid = [p for p in paths if os.path.isfile(p)]
        invalid = [p for p in paths if p and not os.path.isfile(p)]

        if valid:
            self.file_list.add_files(valid)
        if invalid:
            QMessageBox.warning(
                self, "Invalid Paths",
                "The following paths were not found:\n" + "\n".join(f"  {p}" for p in invalid),
            )

    def _add_folder(self) -> None:
        """Scan a directory (non-recursive) and add all audio/video files found.
        Falls back to subprocess ls when os.scandir fails (common WSL2/NTFS issue).
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return

        filenames = self._list_dir(folder)
        if filenames is None:
            QMessageBox.warning(self, "Folder Error", f"Could not read folder:\n{folder}")
            return

        paths = [
            os.path.join(folder, f)
            for f in filenames
            if os.path.splitext(f)[1].lower() in AUDIO_VIDEO_EXT
        ]
        if paths:
            self.file_list.add_files(sorted(paths))

    @staticmethod
    def _list_dir(folder: str) -> list[str] | None:
        """Return filenames in folder. Falls back to subprocess ls on OSError."""
        import subprocess

        # Primary: standard Python directory listing
        try:
            return os.listdir(folder)
        except OSError:
            pass

        # Fallback: invoke ls and parse stdout (works even when getdents syscall fails)
        try:
            result = subprocess.run(
                ["ls", folder],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 or result.stdout.strip():
                return [f for f in result.stdout.splitlines() if f]
        except Exception:
            pass

        return None

    # ── player integration ───────────────────────────────────────────────

    def _on_file_selected(self, path: str) -> None:
        self._current_path = path
        self.player.load_file(path)
        # Range will be restored once duration is known in _on_duration_loaded

    def _on_duration_loaded(self, duration_ms: int) -> None:
        """Restore the saved clip range once the player reports the file duration."""
        if duration_ms <= 0 or self._current_path is None:
            return
        for entry in self.file_list.entries:
            if entry.input_path == self._current_path:
                self.player.restore_range(entry.start_ms, entry.end_ms)
                break

    def _on_range_changed(self, start_ms: int, end_ms: int) -> None:
        """Convert slider values to Optional[int] and write back to the FileEntry."""
        if self._current_path is None:
            return
        duration = self.player._player.duration()
        s = start_ms if start_ms > 0 else None
        e = end_ms if duration > 0 and end_ms < duration else None
        self.file_list.update_range(self._current_path, s, e)

    # ── processing ───────────────────────────────────────────────────────

    def _start_processing(self) -> None:
        enabled = self.file_list.get_enabled_entries()
        if not enabled:
            QMessageBox.warning(self, "Warning", "No files selected.")
            return

        global_params = self.settings_panel.get_params()
        if not global_params.output_dir:
            QMessageBox.warning(self, "Warning", "Please set an output directory first.")
            return

        tasks: list[AudioTask] = []
        for entry in enabled:
            params = entry.get_params(global_params)
            out_dir = params.output_dir or global_params.output_dir
            tasks.append(
                AudioTask(
                    input_path=entry.input_path,
                    output_dir=out_dir,
                    start_ms=entry.start_ms,
                    end_ms=entry.end_ms,
                    format=params.format,
                    sample_rate=params.sample_rate,
                    bit_depth=params.bit_depth,
                    channels=params.channels,
                    normalize=params.normalize,
                    normalize_dbfs=params.normalize_dbfs,
                )
            )

        self.file_list.reset_statuses()
        self.log_panel.clear()
        self.log_panel.set_progress(0, len(tasks))
        self._set_ui_locked(True)

        self._worker = ProcessingWorker(tasks, parent=self)
        self._worker.log_signal.connect(self.log_panel.append)
        self._worker.file_started_signal.connect(
            lambda p: self.file_list.update_status(p, STATUS_PROCESSING)
        )
        self._worker.file_done_signal.connect(self._on_file_done)
        self._worker.progress_signal.connect(self.log_panel.set_progress)
        self._worker.all_done_signal.connect(self._on_all_done)
        self._worker.start()

    def _on_file_done(self, path: str, success: bool, error: str) -> None:
        self.file_list.update_status(
            path,
            STATUS_DONE if success else STATUS_FAILED,
            error,
        )

    def _on_all_done(self, success: int, fail: int) -> None:
        self.log_panel.set_done(success, fail)
        self._set_ui_locked(False)

        if fail == 0:
            QMessageBox.information(
                self, "Done", f"All {success} file(s) processed successfully \u2713"
            )
        else:
            failed = [e for e in self.file_list.entries if e.status == STATUS_FAILED]
            details = "\n".join(f"  \u2022 {e.filename}: {e.error}" for e in failed)
            QMessageBox.warning(
                self,
                "Done with Errors",
                f"\u2713 {success} succeeded  \u2717 {fail} failed\n\nFailures:\n{details}",
            )

    # ── helpers ──────────────────────────────────────────────────────────

    def _set_ui_locked(self, locked: bool) -> None:
        """Disable interactive controls while processing to prevent interference."""
        enabled = not locked
        self._add_btn.setEnabled(enabled)
        self._add_folder_btn.setEnabled(enabled)
        self._paste_btn.setEnabled(enabled)
        self._process_btn.setEnabled(enabled)
        self._sel_all_btn.setEnabled(enabled)
        self._desel_btn.setEnabled(enabled)
        self.settings_panel.setEnabled(enabled)
        self.file_list.setEnabled(enabled)
        self.player.setEnabled(enabled)
