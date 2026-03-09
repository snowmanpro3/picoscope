"""
PICOSKOPE MEASUREMENT
"""

# Импортируем сгенерированный класс. Команда: pyuic6 gui_layout.ui -o gui_layout.py
import sys
from gui_layout import Ui_MainWindow
from pico5000SDK import PicoScope5000A as pico5000
from PyQt6 import QtGui
import io
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QPlainTextEdit, QTabWidget
from PyQt6.QtGui import QTextCursor, QColor
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal, QThread, pyqtSlot
# from workers import SingleAxisWorker

# from __future__ import division, print_function
# import time
# import numpy as np
# import csv
# import matplotlib.pyplot as plt
# import traceback


class Picoscope_thermocouple_GUI(QMainWindow):
    """
    Класс, связывающий класс GUI с классом поведения пикоскопа
    """
    def __init__(self):
        super().__init__()

        self.gui = Ui_MainWindow() #! Теперь обращение к кнопкам через self.gui.push_button например
        self.gui.setupUi(self)  # Инициализация интерфейса (на этом использование gui_layout - всё, остальное - кнопки)
        self.dual_print("Программа запущена!")
        self.pico = None

        self.worker = None

        self._setup_logger(self.gui.Console) # Настройка консоли для вывода принтов

            # "axis_obj": None, #!Здесь хранятся ссылки на ось как объект из модуля newACS, к которым можно применять его методы

        self.params = {
            'channel': None,
            'range': None,
            'acdc_choice': None,
            'meas_time': None,
            'discFrequency': None,
            't_channel': None,
            't_treshold': None,
            't_direction': None,
            't_delay': None,
            't_auto_time': None,
            'trigger_choice': None,
        }

        self.connect_ui_elements() # Подключаем функции к элементам интерфейс
        self.set_default_values() 
    
    def connect_to_pico(self):
        if self.gui.connect_button.text() == "CONNECT":
            """Подключается к пикоскопу. Инициализирует оси как объекты в ключе 'axis_obj """
            self.pico = pico5000()
            status = self.pico.open()
            print(status)
            self.dual_print(f"Статус подключения:{self.pico.is_open}")
            self.gui.connect_button.setText("DISCONNECT")
            self.gui.connect_status.setStyleSheet("background-color:rgb(0, 128, 0)")

        elif self.gui.connect_button.text() == "DISCONNECT":
            """Отключается от пикоскопа. Удаляет объекты из ключа 'axis_obj' """
            if self.pico is not None and self.pico.is_open:
                try:
                    self.pico.close()
                    self.dual_print("Соединение с PicoScope закрыто")
                except Exception as e:
                    self.dual_print(f"Ошибка при закрытии соединения: {e}")
            else:
                self.dual_print("PicoScope не был подключен или уже закрыт")
            self.gui.connect_button.setText("CONNECT")
            self.gui.connect_status.setStyleSheet("background-color:rgb(255, 0, 0)")

    def closeEvent(self, event):
        """
        Переопределение метода закрытия окна на крестик или ALT+F4
        """
        self.dual_print("Завершение работы программы...")
        
        # Проверяем, был ли подключен пикоскоп
        if self.pico is not None:
            if self.pico.is_open:
                try:
                    self.pico.close()
                    self.dual_print("Соединение с PicoScope закрыто")
                except Exception as e:
                    self.dual_print(f"Ошибка при закрытии соединения: {e}")
                    # Всё равно продолжаем закрытие программы
            else:
                self.dual_print("PicoScope не был подключен")
        else:
            self.dual_print("PicoScope не был даже инициализирован")
        event.accept() # Принимаем событие закрытия (окно закроется)


    def connect_ui_elements(self):
        self.gui.connect_button.clicked.connect(self.connect_to_pico)
        self.gui.reset_button.clicked.connect(self.set_default_values)
        # self.gui.start_button.clicked.connect(self.start)
        # self.gui.stop_button.clicked.connect(self.stop_all_axes)
        
        '''Перед connect стоит т.н. сигнал, а сам connect связывает сигнал с обработчиком'''
        self.gui.channel_input.textChanged.connect(lambda text: self.params.update({'channel': text.strip()}))
        self.gui.range_choice.currentTextChanged.connect(lambda text: self.params.update({'range': text.strip()}))
        self.gui.acdc_choice.currentTextChanged.connect(lambda text: self.params.update({'acdc_choice': text.strip()}))
        self.gui.meas_time_input.textChanged.connect(lambda text: self.params.update({'meas_time': text.strip()}))
        self.gui.discFrequency_input.textChanged.connect(lambda text: self.params.update({'discFrequency': text.strip()})) #! А нужно ли???
        self.gui.t_channel_input.textChanged.connect(lambda text: self.params.update({'t_channel': text.strip()}))
        self.gui.t_treshold_input.textChanged.connect(lambda text: self.params.update({'t_treshold': text.strip()}))
        self.gui.t_direction_input.currentTextChanged.connect(lambda text: self.params.update({'t_direction': text.strip()}))
        self.gui.t_delay_input.textChanged.connect(lambda text: self.params.update({'t_delay': text.strip()}))
        self.gui.t_auto_time_input.textChanged.connect(lambda text: self.params.update({'t_auto_time': text.strip()}))
        self.gui.trigger_choice.stateChanged.connect(
            lambda state: self.params.update({'trigger_choice': 1 if state == 2 else 0})
            )
        
    def set_default_values(self): # Выставляет дефолтные параметры движения осей в общем окне
        self.gui.channel_input.setText("A")
        self.gui.range_choice.setCurrentText("200mV")
        self.gui.acdc_choice.setCurrentText("DC")
        self.gui.meas_time_input.setText("100") #! Какие единицы измерения? нс, мкс, мс?
        self.gui.discFrequency_input.setText("1000000")
        self.gui.t_channel_input.setText("A")
        self.gui.t_treshold_input.setText("40")
        self.gui.t_delay_input.setText("0")
        self.gui.t_auto_time_input.setText("0")

    def _setup_logger(self, log_window=None):
        """Приватный метод для настройки логгера"""
        if log_window == None:
            log_window = self.Console
        log_window.setReadOnly(True) # Лог только для чтения
        log_window.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap) # Отключаем перенос строк
        
        # Задаем шрифт с одинаковой шириной всех символов
        font = log_window.font()
        font.setFamily("Courier New")  # Моноширинный шрифт
        log_window.setFont(font)

    def dual_print(self, message, log_window=None):
        if log_window == None:
            log_window = self.gui.Console
        print(message)  # Консольный вывод
        log_window.appendPlainText(message)  # GUI-вывод
        cursor = log_window.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        log_window.setTextCursor(cursor)

    def start(self):
        self.pico.configure(self.params) #!!!! Недоделано



if __name__ == '__main__':
    app = QApplication([])
    window = Picoscope_thermocouple_GUI()
    window.show()
    sys.exit(app.exec())
    # window.axisstate()
    # print(ACSControllerGUI.__dict__) # Shows all attributes the object have