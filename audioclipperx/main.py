import multiprocessing
import sys


# Priority-ordered font paths to try for CJK support
# WSL2 can read Windows fonts directly from /mnt/c/Windows/Fonts/
_CJK_FONT_CANDIDATES = [
    "/mnt/c/Windows/Fonts/msyh.ttc",
    "/mnt/c/Windows/Fonts/simhei.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
]


def _setup_font(app) -> None:
    """Load a CJK-capable font so filenames with Chinese characters render correctly."""
    from PySide6.QtGui import QFont, QFontDatabase

    for path in _CJK_FONT_CANDIDATES:
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                app.setFont(QFont(families[0], 9))
                return

    # Fallback: let Qt pick from system fonts that support CJK
    font = QFont()
    font.setFamilies(["Microsoft YaHei", "SimHei", "Noto Sans CJK SC",
                      "WenQuanYi Micro Hei", "DejaVu Sans"])
    font.setPointSize(9)
    app.setFont(font)


def main() -> None:
    # Required on Windows/WSL for ProcessPoolExecutor to work correctly
    multiprocessing.freeze_support()

    from PySide6.QtWidgets import QApplication
    from audioclipperx.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("AudioClipperX")
    app.setStyle("Fusion")

    _setup_font(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
