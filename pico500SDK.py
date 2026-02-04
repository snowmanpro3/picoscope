from picosdk.ps5000a import ps5000a as ps
from picosdk.functions import adc2mV, assert_pico_ok
print('ok')


class PicoScope5000A:


    def open(self): ...


    def configure(self, params): ...


    def acquire_block(self): ...


    def get_data(self): ...