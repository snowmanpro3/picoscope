params = {  
    'channel': None,
    'range': 200,
    'range_units_choice': 'mV',
    'acdc_choice': None,
    'meas_time': None,
    't_channel': None,
    't_treshold': None,
    't_direction': None,
    't_delay': None,
    't_auto_time': None,
    'trigger_choice': None,
}


print(f"PS5000A_{params['range']}{params['range_units_choice'].upper()}")