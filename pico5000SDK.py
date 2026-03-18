from picosdk.ps5000a import ps5000a as ps
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc
import ctypes
import matplotlib.pyplot as plt
import numpy as np
import time


class PicoScope5000A:
    def __init__(self, resolution="PS5000A_DR_16BIT", log_func=print):
        self.log = log_func
        self.chandle = ctypes.c_int16() #! Дискриптор? Идентификатор? Номерок в гардеробе?
        self.status = {}
        self.resolution = ps.PS5000A_DEVICE_RESOLUTION[resolution] # Разрешение 16 бит максимум
        self.is_open = False

        # состояние измерительной части
        self.range = None
        self.maxADC = None
        self.timebase = None
        self.dt = None
        self.N = None

    def open(self):
        status = ps.ps5000aOpenUnit(
            ctypes.byref(self.chandle),
            None,
            self.resolution
        )

        if status in (282, 286): # Обработка ошибок подключения
            ps.ps5000aChangePowerSource(self.chandle, status)
        else:
            assert_pico_ok(status) #! Эта функция сама возвращает ошибку, если status !=0

        self.is_open = True

    def configure_channel(self, params: dict):
        """
        Функция настраивает канал в соответствии с параметрами из словаря params:
        - channel: канал (A, B, C или D)
        - acdc_choice: тип подключения (AC или DC)
        - range: диапазон измерений (например, 200mV, 500mV, 1V и т.д.)
        -maxADC: максимальное значение АЦП для выбранного диапазона (ps5000aMaximumValue).
            Нужно для дальнейших расчетов при преобразовании данных из АЦП в мВ.
        """
        if not self.is_open:
            raise RuntimeError("PicoScope is not open")
        
        # handle = chandle
        self.channel = ps.PS5000A_CHANNEL[f"PS5000A_CHANNEL_{params['channel'].upper()}"] #*
        self.coupling_type = ps.PS5000A_COUPLING[f"PS5000A_{params['acdc_choice'].upper()}"] #*
        self.chARange = ps.PS5000A_RANGE[f"PS5000A_{params['range'].upper()}"] #! PS5000A_200MV
        status = ps.ps5000aSetChannel(self.chandle, self.channel, 1, self.coupling_type, self.chARange, 0)
        assert_pico_ok(status)

        # Ищем максимальное значение АЦП
        # pointer to value = ctypes.byref(maxADC)
        self.maxADC = ctypes.c_int16()
        status = ps.ps5000aMaximumValue(self.chandle, ctypes.byref(self.maxADC))
        self.maxADC_int = self.maxADC.value # Значение максимального АЦП
        assert_pico_ok(status)

        self.log(f"Канал {params['channel']} настроен: {params['range']}, {params['acdc_choice']}")

    def configure_trigger(self, params: dict):
        """
        Функция настраивает триггер по заданным параметрам.
            - t_channel: канал, на котором сработает триггер
            - t_treshold: порог срабатывания в мВ
            - t_direction: направление срабатывания (RISING, FALLING, ABOVE, BELOW)
            - t_delay: задержка после срабатывания триггера (по дефолту 0)
            - t_auto_time: время в мс для автоматического срабатывания триггера (по дефолту 0, т.е. отключено)
            - trigger_choice: включение (1) или отключение (0) триггера
        """

        #!!!!     'trigger_choice': None,
        #!     'trigger_choice': None,
        #!     'trigger_choice': None, ДОДЕЛАТЬ ВЫКЛЮЧЕНИЕ ТРИГГЕРА

        # Set up an advanced trigger in mv
        self.adcTriggerLevel = mV2adc(params['t_treshold'], self.chARange, self.maxADC)

        simple_trigger = ps.ps5000aSetSimpleTrigger(
            self.chandle,
            params['trigger_choice'],  #! 1 - enable, 0 - disable
            self.channel, # channel
            self.adcTriggerLevel, # treshold
            ps.PS5000A_THRESHOLD_DIRECTION[f"PS5000A_{params['t_direction'].upper()}"], # ABOVE, BELOW, RISING, FALLING, etc.
            params['t_delay'],  # delay (по дефолту 0)
            params['t_auto_time']   # auto trigger time in ms (по дефолту 0)
        )
        assert_pico_ok(simple_trigger)

        self.log('Триггер успешно настроен')
    
    def configure_timebase(self, params: dict):
        """
        Настройка временной базы PicoScope.

        params:
            meas_time       время измерения (мс)
            discFrequency   частота дискретизации (Гц)
        """

        if not self.is_open:
            raise RuntimeError("PicoScope is not open")
        
        min_timebase = ctypes.c_uint32()
        min_timeInterval_sec = ctypes.c_double()

        status = ps.ps5000aGetMinimumTimebaseStateless(
            self.chandle,
            ps.PS5000A_CHANNEL_FLAGS["PS5000A_CHANNEL_A"],
            ctypes.byref(min_timebase),
            ctypes.byref(min_timeInterval_sec),
            self.resolution
        )

        assert_pico_ok(status)

        self.log("Minimum timebase:", min_timebase.value)
        self.log("Sampling interval (s):", min_timeInterval_sec.value)

        dt_limit = params["dt_limit"]

        timeIntervalns = ctypes.c_float() # Единицы измерения - наносекунды
        returnedMaxSamples = ctypes.c_int32()

        for timebase in range(min_timebase.value, 10000): #* Для 16-бит минимальная таймбейз = 4 (16 нс)

            status = ps.ps5000aGetTimebase2(
                self.chandle,
                timebase,
                1,
                ctypes.byref(timeIntervalns),
                ctypes.byref(returnedMaxSamples),
                0
            )

            if status != 0:
                continue

            dt = timeIntervalns.value * 1e-9

            if dt <= dt_limit:
                self.timebase = timebase #* Номер временной базы
                self.dt = dt #* Реальный шаг по времени для выбранной временной базы в секундах
                break

        if self.timebase is None:
            raise RuntimeError("No suitable timebase found for given dt_limit")

        meas_time = params["meas_time"] / 1000
        self.N = int(meas_time / self.dt) #! хз, нужно ли
        timeIntervalns = ctypes.c_float()
        returnedMaxSamples2 = ctypes.c_int32()

        status = ps.ps5000aGetTimebase2( # Получаем maxSamples для выбранного timebase через супер большое число точек (10кк)
            self.chandle,
            self.timebase,
            10_000_000,
            ctypes.byref(timeIntervalns),
            ctypes.byref(returnedMaxSamples2),
            0
        )

        assert_pico_ok(status)

        self.maxSamples = returnedMaxSamples2.value

        self.log(f'TimeBase: {self.timebase} s')
        self.log(f'Initial number of samples: {self.N}')
        self.log(f'Max samples: {self.maxSamples}')
        self.N = min(self.N, self.maxSamples)
        self.log(f'Number of samples: {self.N}, Max Samples {self.maxSamples}')


    def start_measurement(self, params: dict):
        """
        Запускает измерение с текущими настройками канала, триггера и временной базы.
        """

        # Set number of pre and post trigger samples to be collected
        preTriggerSamples = self.N // 2
        postTriggerSamples = self.N - preTriggerSamples
        maxSamples = preTriggerSamples + postTriggerSamples

        status = ps.ps5000aRunBlock(self.chandle, preTriggerSamples, postTriggerSamples, self.timebase, None, 0, None, None)
        assert_pico_ok(status)

        # Check for data collection to finish using ps5000aIsReady
        ready = ctypes.c_int16(0)
        check = ctypes.c_int16(0)
        while ready.value == check.value:
            status = ps.ps5000aIsReady(self.chandle, ctypes.byref(ready))
            time.sleep(0.001)

        # Create buffers ready for assigning pointers for data collection
        bufferAMax = (ctypes.c_int16 * maxSamples)()
        bufferAMin = (ctypes.c_int16 * maxSamples)() # used for downsampling which isn't in the scope of this example


        # Set data buffer location for data collection from channel A
        # handle = chandle
        source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
        # pointer to buffer max = ctypes.byref(bufferAMax)
        # pointer to buffer min = ctypes.byref(bufferAMin)
        # buffer length = maxSamples
        # segment index = 0
        # ratio mode = PS5000A_RATIO_MODE_NONE = 0
        status= ps.ps5000aSetDataBuffers(self.chandle, source, ctypes.byref(bufferAMax), ctypes.byref(bufferAMin), maxSamples, 0, 0)
        assert_pico_ok(status)

        # create overflow loaction
        overflow = ctypes.c_int16()
        # create converted type maxSamples
        cmaxSamples = ctypes.c_int32(maxSamples)

        # Retried data from scope to buffers assigned above
        # handle = chandle
        # start index = 0
        # pointer to number of samples = ctypes.byref(cmaxSamples)
        # downsample ratio = 0
        # downsample ratio mode = PS5000A_RATIO_MODE_NONE
        # pointer to overflow = ctypes.byref(overflow))
        status = ps.ps5000aGetValues(self.chandle, 0, ctypes.byref(cmaxSamples), 0, 0, 0, ctypes.byref(overflow))
        assert_pico_ok(status)

        actual_samples = cmaxSamples.value

        # convert ADC counts data to mV
        adc2mVChAMax =  adc2mV(bufferAMax, self.chARange, self.maxADC)

        time = np.linspace(0, (actual_samples - 1) * self.dt, actual_samples)

        # plot data from channel A and B
        plt.plot(time, adc2mVChAMax[:])
        plt.xlabel('Time (ns)')
        plt.ylabel('Voltage (mV)')
        plt.show()

        # Stop the scope
        # handle = chandle
        status = ps.ps5000aStop(self.chandle)
        assert_pico_ok(status)




    def close(self):
        if self.is_open:
            ps.ps5000aCloseUnit(self.chandle)
            self.is_open = False



if __name__ == "__main__":
    scope = PicoScope5000A()

    print("Opening PicoScope...")
    scope.open()

    print("Configuring channel A...")
    scope.configure({
        "channel": "A",
        "range": "PS5000A_200MV",
        "coupling": "PS5000A_DC"
    })

    print("OK: PicoScope connected and configured")

    scope.close()
    print('PicoScope closed successfully')