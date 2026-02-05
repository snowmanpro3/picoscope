from picosdk.ps5000a import ps5000a as ps
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc
import ctypes


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

        # Set up an advanced trigger
        adcTriggerLevelA = mV2adc(30, chARange, maxADC)

        simple_trigger = ps.ps5000aSetSimpleTrigger(
            self.chandle,
            1,  # enable
            channel, # channel
            adcTriggerLevelA, # treshold
            ps.PS5000A_THRESHOLD_DIRECTION["PS5000A_RISING"], # ABOVE, BELOW, RISING, FALLING, etc.
            0,  # delay
            0   # auto trigger time in ms
        )




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
        "range": "PS5000A_20V",
        "coupling": "PS5000A_DC"
    })

    print("OK: PicoScope connected and configured")

    scope.close()
    print('PicoScope closed successfully')