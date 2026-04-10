from concurrent.futures import ProcessPoolExecutor, as_completed

from PySide6.QtCore import QThread, Signal

from audioclipperx.models import AudioTask
from audioclipperx.processor import process_file


class ProcessingWorker(QThread):
    log_signal = Signal(str)
    file_started_signal = Signal(str)          # input_path
    file_done_signal = Signal(str, bool, str)  # input_path, success, error
    progress_signal = Signal(int, int)          # completed, total
    all_done_signal = Signal(int, int)          # success_count, fail_count

    def __init__(self, tasks: list[AudioTask], parent=None):
        super().__init__(parent)
        self.tasks = tasks

    def run(self):
        total = len(self.tasks)
        success_count = 0
        fail_count = 0

        for task in self.tasks:
            self.file_started_signal.emit(task.input_path)

        with ProcessPoolExecutor() as executor:
            future_to_path = {
                executor.submit(process_file, task): task.input_path
                for task in self.tasks
            }

            completed = 0
            for future in as_completed(future_to_path):
                result = future.result()

                for log_line in result.logs:
                    self.log_signal.emit(log_line)

                completed += 1
                self.progress_signal.emit(completed, total)

                if result.success:
                    success_count += 1
                    self.file_done_signal.emit(result.input_path, True, "")
                else:
                    fail_count += 1
                    self.file_done_signal.emit(
                        result.input_path, False, result.error or ""
                    )

        self.log_signal.emit("─" * 40)
        self.log_signal.emit(
            f"Finished: ✓ {success_count} succeeded, ✗ {fail_count} failed"
        )
        self.all_done_signal.emit(success_count, fail_count)
