from PySide6.QtCore import Qt, QItemSelectionModel
from PySide6.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QLabel,
)
from PySide6.QtWidgets import QDialog, QProgressBar, QMessageBox, QTableWidget, QTableWidgetItem
from PySide6.QtCore import QThread, Signal, Qt, QSize


class WorkerThread(QThread):
    progress_changed = Signal(int, str)
    finished = Signal()
    canceled = Signal()

    def __init__(self, inst):
        super().__init__()
        self._is_interrupted = False
        self.inst = inst

    def run(self):
        try:
            self.inst.progress_callback = self.progress_callback
            self.inst.is_interrupted = lambda: self._is_interrupted
            success = self.inst.process()
            if not success:
                self.canceled.emit()
            else:
                self.finished.emit()
        except Exception as e:
            print(f"[WorkerThread] 예외 발생: {e}")
            self.canceled.emit()

    def progress_callback(self, value, status=""):
        self.progress_changed.emit(value, status)

    def cancel(self):
        self._is_interrupted = True



class ProgressWindow(QDialog):
    def __init__(self, parent, inst):
        super().__init__(parent)
        self.setWindowTitle("Processing...")
        self.setFixedSize(300, 120)

        layout = QVBoxLayout(self)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Loading ...")
        layout.addWidget(self.status_label)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_task)
        layout.addWidget(self.cancel_button)

        self._was_canceled = False
        self._done = False

        self.worker = WorkerThread(inst)
        self.worker.progress_changed.connect(self.update_progress, Qt.QueuedConnection)
        self.worker.finished.connect(self.on_finished)
        self.worker.canceled.connect(self.on_canceled)
        self.worker.start()

    def update_progress(self, value: int, status: str):
        self.progress_bar.setValue(value)
        self.status_label.setText(status)

    def cancel_task(self):
        self._was_canceled = True
        self.worker.cancel()

    def on_finished(self):
        if self._done:
            return
        self._done = True
        self.accept()

    def on_canceled(self):
        if self._done:
            return
        self._done = True
        self.reject()
