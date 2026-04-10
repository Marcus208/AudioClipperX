from PySide6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
)

from audioclipperx.models import FORMATS, SAMPLE_RATES, BIT_DEPTHS, FileParams


class SettingsPanel(QGroupBox):
    """Global default output parameters shown at the top of the main window."""

    def __init__(self, parent=None):
        super().__init__("Global Default Parameters", parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        # Format
        layout.addWidget(QLabel("Format:"))
        self._fmt = QComboBox()
        self._fmt.addItems(FORMATS)
        self._fmt.setCurrentText("wav")
        layout.addWidget(self._fmt)
        layout.addSpacing(10)

        # Sample rate
        layout.addWidget(QLabel("Sample Rate:"))
        self._sr = QComboBox()
        self._sr.addItems([str(r) for r in SAMPLE_RATES])
        self._sr.setCurrentText("48000")
        layout.addWidget(self._sr)
        layout.addSpacing(10)

        # Bit depth
        layout.addWidget(QLabel("Bit Depth:"))
        self._bd = QComboBox()
        self._bd.addItems([str(b) for b in BIT_DEPTHS])
        self._bd.setCurrentText("24")
        layout.addWidget(self._bd)
        layout.addSpacing(10)

        # Channels
        layout.addWidget(QLabel("Channels:"))
        self._ch = QComboBox()
        self._ch.addItems(["Mono", "Stereo"])
        self._ch.setCurrentIndex(1)
        layout.addWidget(self._ch)
        layout.addSpacing(10)

        # Normalize
        self._normalize = QCheckBox("Normalize")
        self._normalize.setToolTip("Apply peak normalization to make all files the same loudness")
        self._normalize.toggled.connect(self._on_normalize_toggled)
        layout.addWidget(self._normalize)
        self._norm_lbl = QLabel("Target:")
        layout.addWidget(self._norm_lbl)
        self._norm_dbfs = QDoubleSpinBox()
        self._norm_dbfs.setRange(-60.0, 0.0)
        self._norm_dbfs.setSingleStep(0.5)
        self._norm_dbfs.setValue(-1.0)
        self._norm_dbfs.setSuffix(" dBFS")
        self._norm_dbfs.setFixedWidth(90)
        layout.addWidget(self._norm_dbfs)
        self._on_normalize_toggled(False)
        layout.addSpacing(10)

        # Output directory
        layout.addWidget(QLabel("Output Dir:"))
        self._out_dir = QLineEdit()
        self._out_dir.setPlaceholderText("Select output directory...")
        self._out_dir.setMinimumWidth(180)
        layout.addWidget(self._out_dir, 1)
        browse = QPushButton("Browse")
        browse.clicked.connect(self._browse)
        layout.addWidget(browse)

    def _on_normalize_toggled(self, checked: bool) -> None:
        self._norm_lbl.setEnabled(checked)
        self._norm_dbfs.setEnabled(checked)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self._out_dir.setText(path)

    # ── public API ───────────────────────────────────────────────────────

    def get_params(self) -> FileParams:
        return FileParams(
            format=self._fmt.currentText(),
            sample_rate=int(self._sr.currentText()),
            bit_depth=int(self._bd.currentText()),
            channels=self._ch.currentIndex() + 1,
            output_dir=self._out_dir.text().strip(),
            normalize=self._normalize.isChecked(),
            normalize_dbfs=self._norm_dbfs.value(),
        )

    def set_params(self, params: FileParams) -> None:
        self._fmt.setCurrentText(params.format)
        self._sr.setCurrentText(str(params.sample_rate))
        self._bd.setCurrentText(str(params.bit_depth))
        self._ch.setCurrentIndex(params.channels - 1)
        self._out_dir.setText(params.output_dir)
        self._normalize.setChecked(params.normalize)
        self._norm_dbfs.setValue(params.normalize_dbfs)
