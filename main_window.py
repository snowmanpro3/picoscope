"""
PICOSKOPE MEASUREMENT
"""

# Импортируем сгенерированный класс. Команда: pyuic6 gui_layout.ui -o gui_layout.py
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
    def __init__(self):
        super().__init__()

        self.gui = Ui_MainWindow() #! Теперь обращение к кнопкам через self.gui.push_button например
        self.gui.setupUi(self)  # Инициализация интерфейса (на этом использование gui_layout - всё, остальное - кнопки)
        self.dual_print("Программа запущена!")
        self.pico = None

        self.worker = None

        self._setup_logger(self.gui.Console) # Настройка консоли для вывода принтов

            # "axis_obj": None, #!Здесь хранятся ссылки на ось как объект из модуля newACS, к которым можно применять его методы
    
        self.connect_ui_elements() # Подключаем функции к элементам интерфейса


    def connect_ui_elements(self):
        # self.gui.connect_button.clicked.connect(self.connect_to_pico)
        # self.gui.reset_button.clicked.connect(self.set_default_values)
        # self.gui.start_button.clicked.connect(self.start)
        # self.gui.stop_button.clicked.connect(self.stop_all_axes)
        
        #!!!! А стоит ли сразу передавать эти значения. Может легче всё связать с функцией старта
        #!!!! в которой будет проверка на заполнение пустых полей в qTextEdit
        '''Перед connect стоит т.н. сигнал, а сам connect связывает сигнал с обработчиком'''
        self.gui.channel_input.textChanged.connect(lambda text: self.set_speed(text))
        self.gui.range_input.textChanged.connect(lambda text: self.set_acceleration(text))
        self.gui.range_units_choice.currentTextChanged.connect(lambda text: self.enable_or_disable_mode_data(text))
        self.gui.acdc_choice.currentTextChanged.connect(lambda text: self.enable_or_disable_mode_data(text))
        self.gui.meas_time_input.textChanged.connect(lambda text: self.set_kill_deceleration(text))
        self.gui.t_channel_input.textChanged.connect(lambda text: self.set_jerk(text))
        self.gui.t_treshold_input.textChanged.connect(lambda text: self.set_move_distance(text))
        self.gui.t_direction_input.currentTextChanged.connect(lambda checked: self.toggle_axis())
        self.gui.t_delay_input.textChanged.connect(lambda checked: self.start())
        self.gui.t_auto_time_input.textChanged.connect(lambda checked: self.start())
        self.gui.trigger_choose.stateChanged.connect(lambda state: self.update_selected_axes(state))
        


    def set_default_values(self): # Выставляет дефолтные параметры движения осей в общем окне
        self.gui.channel_input.setText("A")
        self.gui.range_input.setText("200")
        self.gui.meas_time_input.setText("100") #! Какие единицы измерения? нс, мкс, мс?
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

    def connect_to_pico(self):
        """Подключается к пикоскопу. Инициализирует оси как объекты в ключе 'axis_obj """
        self.pico = pico5000()
        status = pico5000.open()
        print(status)
        self.dual_print(f"Статус подключения:{self.pico.is_open}")



if __name__ == '__main__':
    app = QApplication([])
    window = Picoscope_thermocouple_GUI()
    window.show()
    app.exec()
    # window.axisstate()
    # print(ACSControllerGUI.__dict__) # Shows all attributes the object have