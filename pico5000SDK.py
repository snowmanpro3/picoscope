from picosdk.ps5000a import ps5000a as ps
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc
import ctypes
import matplotlib.pyplot as plt
import numpy as np


class PicoScope5000A:
    def __init__(self, resolution="PS5000A_DR_16BIT"):
        self.chandle = ctypes.c_int16()
        self.status = {}
        self.resolution = ps.PS5000A_DEVICE_RESOLUTION[resolution]
        self.is_open = False

    def open(self):
        status = ps.ps5000aOpenUnit(
            ctypes.byref(self.chandle),
            None,
            self.resolution
        )

        if status in (282, 286):
            ps.ps5000aChangePowerSource(self.chandle, status)
        else:
            assert_pico_ok(status)

        self.is_open = True

    def configure(self, params):
        if not self.is_open:
            raise RuntimeError("PicoScope is not open")
        

        # Set up channel A
        # handle = chandle
        channel = ps.PS5000A_CHANNEL[f"PS5000A_CHANNEL_{params['channel'].upper()}"]
        coupling_type = ps.PS5000A_COUPLING["PS5000A_DC"]
        chARange = ps.PS5000A_RANGE[params['range']]
        status = ps.ps5000aSetChannel(self.chandle, channel, 1, coupling_type, chARange, 0)
        assert_pico_ok(status)

        # find maximum ADC count value
        # handle = chandle
        # pointer to value = ctypes.byref(maxADC)
        maxADC = ctypes.c_int16()
        status = ps.ps5000aMaximumValue(self.chandle, ctypes.byref(maxADC))
        assert_pico_ok(status)

        # Set up an advanced trigger in mv
        adcTriggerLevelA = mV2adc(40, chARange, maxADC)

        simple_trigger = ps.ps5000aSetSimpleTrigger(
            self.chandle,
            1,  # enable
            channel, # channel
            adcTriggerLevelA, # treshold
            ps.PS5000A_THRESHOLD_DIRECTION["PS5000A_RISING"], # ABOVE, BELOW, RISING, FALLING, etc.
            0,  # delay
            0   # auto trigger time in ms
        )

        # Set number of pre and post trigger samples to be collected
        preTriggerSamples = 1000
        postTriggerSamples = 1000
        maxSamples = preTriggerSamples + postTriggerSamples

        timebase = 8
        # noSamples = maxSamples
        # pointer to timeIntervalNanoseconds = ctypes.byref(timeIntervalns)
        # pointer to maxSamples = ctypes.byref(returnedMaxSamples)
        # segment index = 0
        timeIntervalns = ctypes.c_float()
        returnedMaxSamples = ctypes.c_int32()
        status = ps.ps5000aGetTimebase2(self.chandle, timebase, maxSamples, ctypes.byref(timeIntervalns), ctypes.byref(returnedMaxSamples), 0)
        assert_pico_ok(status)

        status = ps.ps5000aRunBlock(self.chandle, preTriggerSamples, postTriggerSamples, timebase, None, 0, None, None)
        assert_pico_ok(status)

        # Check for data collection to finish using ps5000aIsReady
        ready = ctypes.c_int16(0)
        check = ctypes.c_int16(0)
        while ready.value == check.value:
            status = ps.ps5000aIsReady(self.chandle, ctypes.byref(ready))

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

        # convert ADC counts data to mV
        adc2mVChAMax =  adc2mV(bufferAMax, chARange, maxADC)

        time = np.linspace(0, (cmaxSamples.value - 1) * timeIntervalns.value, cmaxSamples.value)

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