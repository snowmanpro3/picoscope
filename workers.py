# workers.py

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
import time


class PicoWorker(QObject):
    data_ready = pyqtSignal(object)   # (t, data)
    log = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, pico, params):
        super().__init__()
        self.pico = pico
        self.params = params
        self._running = True

    def stop(self):
        self._running = False

    @pyqtSlot()
    def run(self):
        """
        Главный метод, который запускается в потоке
        """
        try:
            if self.params['mode'] == 'trigger':
                self.run_trigger()
            else:
                self.run_streaming()

        except Exception as e:
            self.log.emit(f"Ошибка: {e}")

        self.finished.emit()

    def run_trigger(self):
        self.log.emit("Trigger режим")

        t, data = self.pico.start_trigger_measurement(self.params)

        self.data_ready.emit((t, data))

    def run_streaming(self):
        self.log.emit("Streaming режим")

        while self._running:
            t, data = self.pico.get_streaming_data(self.params)

            self.data_ready.emit((t, data))

            time.sleep(0.03)  # ~30 FPS