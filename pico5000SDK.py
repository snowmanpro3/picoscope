from picosdk.ps5000a import ps5000a as ps
from picosdk.functions import assert_pico_ok
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
        self.channel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
        # enabled = 1
        coupling_type = ps.PS5000A_COUPLING["PS5000A_DC"]
        chARange = ps.PS5000A_RANGE["PS5000A_20V"]
        # analogue offset = 0 V
        status = ps.ps5000aSetChannel(self.chandle, self.channel, 1, coupling_type, chARange, 0)
        assert_pico_ok(status)

        print("Configure called with:", params)
        # здесь позже будет ps5000aSetChannel, trigger и т.д.

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