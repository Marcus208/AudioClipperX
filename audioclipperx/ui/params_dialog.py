from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
)

from audioclipperx.models import FORMATS, SAMPLE_RATES, BIT_DEPTHS, FileParams


class FileParamsDialog(QDialog):
    """Per-file parameter override dialog."""

    def __init__(
        self,
        filename: str,
        current_params: FileParams,
        global_params: FileParams,
        has_custom: bool,
        parent=None,
    ):
        super().__init__(parent)
        self._global = global_params
        self.setWindowTitle(f"Parameters \u2014 {filename}")
        self.setMinimumWidth(440)
        self._build_ui(current_params, has_custom)

    def _build_ui(self, params: FileParams, has_custom: bool) -> None:
        layout = QVBoxLayout(self)

        # Toggle for enabling custom parameters
        self._custom_check = QCheckBox("Use custom parameters (override global defaults)")
        self._custom_check.setChecked(has_custom)
        self._custom_check.toggled.connect(self._on_toggled)
        layout.addWidget(self._custom_check)

        # Parameter fields
        self._group = QGroupBox()
        form = QVBoxLayout(self._group)

        def _row(label: str, widget) -> None:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(88)
            row.addWidget(lbl)
            row.addWidget(widget)
            form.addLayout(row)

        self._fmt = QComboBox()
        self._fmt.addItems(FORMATS)
        _row("Format:", self._fmt)

        self._sr = QComboBox()
        self._sr.addItems([str(r) for r in SAMPLE_RATES])
        _row("Sample Rate:", self._sr)

        self._bd = QComboBox()
        self._bd.addItems([str(b) for b in BIT_DEPTHS])
        _row("Bit Depth:", self._bd)

        self._ch = QComboBox()
        self._ch.addItems(["Mono", "Stereo"])
        _row("Channels:", self._ch)

        # Normalize
        norm_row = QHBoxLayout()
        self._normalize = QCheckBox("Normalize volume")
        self._normalize.toggled.connect(self._on_normalize_toggled)
        self._norm_dbfs = QDoubleSpinBox()
        self._norm_dbfs.setRange(-60.0, 0.0)
        self._norm_dbfs.setSingleStep(0.5)
        self._norm_dbfs.setValue(-1.0)
        self._norm_dbfs.setSuffix(" dBFS")
        self._norm_dbfs.setFixedWidth(90)
        norm_row.addWidget(self._normalize)
        norm_row.addWidget(QLabel("Target:"))
        norm_row.addWidget(self._norm_dbfs)
        norm_row.addStretch()
        form.addLayout(norm_row)
        self._on_normalize_toggled(False)

        # Per-file output directory override
        self._out_dir = QLineEdit()
        self._out_dir.setPlaceholderText("Leave blank to use global output directory")
        browse = QPushButton("Browse")
        browse.clicked.connect(self._browse)
        dir_row = QHBoxLayout()
        dir_row.addWidget(self._out_dir)
        dir_row.addWidget(browse)
        lbl = QLabel("Output Dir:")
        lbl.setFixedWidth(88)
        row = QHBoxLayout()
        row.addWidget(lbl)
        row.addLayout(dir_row)
        form.addLayout(row)

        layout.addWidget(self._group)

        # Reset button
        reset_btn = QPushButton("Reset to Global Defaults")
        reset_btn.clicked.connect(self._reset)
        layout.addWidget(reset_btn)

        # OK / Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load(params)
        self._on_toggled(has_custom)

    # ── helpers ──────────────────────────────────────────────────────────

    def _load(self, p: FileParams) -> None:
        self._fmt.setCurrentText(p.format)
        self._sr.setCurrentText(str(p.sample_rate))
        self._bd.setCurrentText(str(p.bit_depth))
        self._ch.setCurrentIndex(p.channels - 1)
        self._normalize.setChecked(p.normalize)
        self._norm_dbfs.setValue(p.normalize_dbfs)
        self._out_dir.setText(p.output_dir)

    def _on_normalize_toggled(self, checked: bool) -> None:
        self._norm_dbfs.setEnabled(checked)

    def _on_toggled(self, checked: bool) -> None:
        self._group.setEnabled(checked)

    def _reset(self) -> None:
        self._load(self._global)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self._out_dir.setText(path)

    # ── result ───────────────────────────────────────────────────────────

    def result_params(self) -> tuple[bool, Optional[FileParams]]:
        """Returns (has_custom, params_or_None)."""
        if not self._custom_check.isChecked():
            return False, None
        return True, FileParams(
            format=self._fmt.currentText(),
            sample_rate=int(self._sr.currentText()),
            bit_depth=int(self._bd.currentText()),
            channels=self._ch.currentIndex() + 1,
            output_dir=self._out_dir.text().strip(),
            normalize=self._normalize.isChecked(),
            normalize_dbfs=self._norm_dbfs.value(),
        )
