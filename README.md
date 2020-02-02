# plugwise
Python library for Plugwise supporting the Adam and Anna (firmware 3.x.y)

Get data like this:

 api = Plugwise('smile', 'abcdefgh', '192.168.xyz.yz', 80)
 
 plugwise_data = api.get_plugwise_data()
 
 print(plugwise_data)
 
 The output looks like this:
 
['Location 1', battery-status, 'setpoint-temp', 'current-temp', {list of presets with temps}, [list of available weekschedules], active schedule, 'last active schedule'], 
['Location 2', battery-status, 'setpoint-temp', 'current-temp', {list of presets with temps}, [list of available weekschedules], active schedule, 'last active schedule'], 
[...],
['Controlled Device', 'boiler-temp', boiler_state, central_heating_state, cooling_state, domestic_hot_water_state, water-pressure, outdoor-temp]]

A `Location` represents an Anna, Lisa, Tom or Floor(?) thermostat. When a Lisa is found, the controlled Tom of Floor is ignored in the output.

The `Controlled Device` represents the heating- or cooling-device that is controlled by the Adam or Smile.

In general, when the vaue is `None` it means the corresponding parameter is not present in the XML-data. For the various `_state` parameters the value can be `True` or `False` when the parameter is found in the XML-data.
