# plugwise
Python library for Plugwise supporting the Adam and Anna (firmware 3.x.y).
This library is based on the work of @laetificat and @CoMPaTech on the haanna-library.

Get data like this:

 ```
 api = plugwise.Plugwise('smile', 'abcdefgh', '192.168.xyz.zyx', 80)
 device = api.get_devices()
 print(data)
 ```
 
The output looks like this:
 
```
[{'name': 'Location_1', 'id': '123abc...'}, {'name': 'Location_2', 'id': '123abc...'}, ... ,{'name': 'Location_x', 'id': '123abc...'}, {'name': 'Controlled_Device', 'id': '123abc...'}]
```

```
for device in devices:
    data = api.get_device_data(device['id'])
    print(data)
```
    
The output looks like this:

```
{'batt status': '0.84', 'active preset': 'home', 'setpoint temp': '20.00', 'current temp': '19.70', 'presets': {'home': 20.0, 'asleep': 17.0, 'away': 15.0, 'vacation': 15.0, 'no_frost': 10.0}, 'available schedules': ['Schedule_1, Schedule_2'], 'selected schedule': 'Schedule_1', 'last used': 'Schedule_1'}
{'batt status': '0.48', 'active preset': 'None', 'setpoint temp': '21.00', 'current temp': '20.93', 'presets': {'home': 20.0, 'asleep': 17.0, 'away': 15.0, 'vacation': 15.0, 'no_frost': 10.0}, 'available schedules': [], 'selected schedule': None, 'last used': None}
...
{'water temp': '80.0', 'boiler state': None, 'central heating state': False, 'cooling state': None, 'domestic hot water state': None, 'boiler pressure': None, 'outdoor temp': '3.0'}
```

A `Location` represents an Anna, Lisa, Tom or Floor(?) thermostat. When a Lisa is found, the controlled Tom of Floor is ignored in the output.

The `Controlled Device` represents the heating- or cooling-device that is controlled by the Adam or Smile.

In general, when the value is `None` it means the corresponding parameter is not present in the XML-data. For the various `_state` parameters the value can be `True` or `False` when the parameter is found in the XML-data.
