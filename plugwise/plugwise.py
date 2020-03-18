"""
Plugwise library for use with Home Assistant Core.
"""
import requests
import xml.etree.cElementTree as Etree

# Time related
import datetime
import pytz
from dateutil.parser import parse

# For XML corrections
import re

PING = "/ping"
DIRECT_OBJECTS = "/core/direct_objects"
DOMAIN_OBJECTS = "/core/domain_objects"
LOCATIONS = "/core/locations"
APPLIANCES = "/core/appliances"
RULES = "/core/rules"


class Plugwise:
    """Define the Plugwise object."""

    def __init__(self, username, password, host, port):
        """Constructor for this class"""
        self._username = username
        self._password = password
        self._endpoint = 'http://' + host + ':' + str(port)

    def ping_gateway(self):
        """Ping the gateway (Adam/Smile) to see if it's online"""
        xml = requests.get(
              self._endpoint + PING,
              auth=(self._username, self._password),
              timeout=10,
        )
        if xml.status_code != 404:
            raise ConnectionError("Could not connect to the gateway.")
        return True
    
    def get_devices(self):
        """Provides the devices-names and application- or location-ids."""
        appliances = self.get_appliances()
        locations = self.get_locations()
        appl_dict = self.get_appliance_dictionary(appliances)
        loc_list = self.get_location_list(locations)
                        
        keys = ['name','id', 'type']
        thermostats = []
        for appl_id,type in appl_dict.items():
            thermostat = []
            if ('heater_central' in type):
               # ('zone_thermostat' not in type)
               #   and ('thermostatic_radiator_valve' not in type)
               #   and ('gateway' not in type)
               #   and ('thermostat' not in type)):
                thermostat.append('Controlled Device')
                thermostat.append(appl_id)
                thermostat.append(type)
                if thermostat != []:
                    thermostats.append(thermostat)
        
        for loc_dict in loc_list:
            thermostat = []
            thermostat.append(loc_dict['name'])
            thermostat.append(loc_dict['id'])
            thermostat.append(loc_dict['type'])
            if thermostat != []:
                thermostats.append(thermostat)

        data = [{k:v for k,v in zip(keys, n)} for n in thermostats]
        return data
                    
    def get_device_data(self, appliances, domain_objects, dev_id, ctrl_id, plug_id):
        """Provides the device-data, based on location_id, from APPLIANCES."""
        outdoor_temp = self.get_outdoor_temperature(domain_objects)
 
        controller_data = {}
        plug_data = {}
        device_data = {}
        if ctrl_id:
            controller_data = self.get_appliance_from_appl_id(ctrl_id)
        if plug_id:
            plug_data = self.get_appliance_from_appl_id(plug_id)
            device_data = plug_data
        if dev_id:
            device_data = self.get_appliance_from_loc_id(domain_objects, dev_id)
            
            preset = self.get_preset_from_id(domain_objects, dev_id)
            presets = self.get_presets_from_id(domain_objects, dev_id)
            schemas = self.get_schema_names_from_id(domain_objects, dev_id)
            last_used = self.get_last_active_schema_name_from_id(domain_objects, dev_id)
            a_sch = []
            l_sch = None
            s_sch = None
            if schemas:
                for a,b in schemas.items():
                   a_sch.append(a)
                   if b == True:
                      s_sch = a
            if last_used:
                l_sch = last_used
            if device_data is not None and device_data['type'] != 'plug':
                device_data.update( {'active_preset': preset} )
                device_data.update( {'presets':  presets} )
                device_data.update( {'available_schedules': a_sch} )
                device_data.update( {'selected_schedule': s_sch} )
                device_data.update( {'last_used': l_sch} )
                if controller_data is not None:
                    device_data.update( {'boiler_state': controller_data['boiler_state']} )
                    device_data.update( {'central_heating_state': controller_data['central_heating_state']} )
                    device_data.update( {'cooling_state': controller_data['cooling_state']} )
                    device_data.update( {'dhw_state': controller_data['dhw_state']} )
        else:
            if 'type' in controller_data:
                if controller_data['type'] == 'heater_central':
                    device_data['type'] = controller_data['type']
                    device_data.update( {'boiler_temp': controller_data['boiler_temp']} )
                    if 'water_pressure' in controller_data:
                        device_data.update( {'water_pressure': controller_data['water_pressure']} )
                    device_data.update( {'outdoor_temp': outdoor_temp} )
                    device_data.update( {'boiler_state': controller_data['boiler_state']} )
                    device_data.update( {'central_heating_state': controller_data['central_heating_state']} )
                    device_data.update( {'cooling_state': controller_data['cooling_state']} )
                    device_data.update( {'dhw_state': controller_data['dhw_state']} )

        return device_data
        
    def set_schedule_state(self, domain_objects, loc_id,name, state):
        """Sets the schedule, with the given name, connected to a location, to true or false - DOMAIN_OBJECTS."""
        self._set_schema_state(domain_objects, loc_id, name, state)
        
    def set_preset(self, loc_id, loc_type, preset):
        """Sets the given location-preset on the relevant thermostat - from DOMAIN_OBJECTS."""
        self._set_preset(loc_id, loc_type, preset)
        
    def set_temperature(self, domain_objects, loc_id, loc_type, temperature):
        """Sends a temperature-set request to the relevant thermostat, connected to a location - from DOMAIN_OBJECTS."""
        self._set_temp(domain_objects, loc_id, loc_type, temperature)

    def get_appliances(self):
        """Collects the appliances XML-data."""
        xml = requests.get(
              self._endpoint + APPLIANCES,
              auth=(self._username, self._password),
              timeout=10,
        )
        if xml.status_code != requests.codes.ok:
            raise ConnectionError("Could not get the appliances.")
        return Etree.fromstring(self.escape_illegal_xml_characters(xml.text))

    def get_locations(self):
        """Collects the locations XML-data."""
        xml = requests.get(
              self._endpoint + LOCATIONS,
              auth=(self._username, self._password),
              timeout=10,
        )
        if xml.status_code != requests.codes.ok:
            raise ConnectionError("Could not get the appliances.")
        return Etree.fromstring(self.escape_illegal_xml_characters(xml.text))

    def get_direct_objects(self):
        """Collects the direct_objects XML-data."""
        xml = requests.get(
              self._endpoint + DIRECT_OBJECTS,
              auth=(self._username, self._password),
              timeout=10,
        )
        if xml.status_code != requests.codes.ok:
            raise ConnectionError("Could not get the direct objects.")
        return Etree.fromstring(self.escape_illegal_xml_characters(xml.text))
    
    def get_domain_objects(self):
        """Collects the domain_objects XML-data."""
        xml = requests.get(
              self._endpoint + DOMAIN_OBJECTS,
              auth=(self._username, self._password),
              timeout=10,
        )
        if xml.status_code != requests.codes.ok:
            raise ConnectionError("Could not get the domain objects.")
        return Etree.fromstring(self.escape_illegal_xml_characters(xml.text))
    
    @staticmethod
    def escape_illegal_xml_characters(root):
        """Replaces illegal &-characters."""
        return re.sub(r'&([^a-zA-Z#])',r'&amp;\1',root)

    def get_appliance_dictionary(self, root):
        """Obtains the existing appliance types and ids - from APPLIANCES."""
        appliance_dictionary = {}
        for appliance in root:
            appliance_name = appliance.find('name').text
            if "Gateway" not in appliance_name:
                appliance_id = appliance.attrib['id']
                appliance_type = appliance.find('type').text
                if appliance_type == 'heater_central':
                    appliance_dictionary[appliance_id] = appliance_type

        return appliance_dictionary
    
    def get_location_list(self,root):
        """Obtains the existing locations and connected applicance_id's - from LOCATIONS."""
        location_list = []
        for location in root:
            location_dict = {}
            location_name = location.find('name').text
            location_id = location.attrib['id']
            appliance_id = None
            location_type =  None
            #for elem in location.iter('appliance'):
            #    if elem.attrib is not None:
            #        appliance_id = elem.attrib['id']
            #for elem in location.iter('relay_functionality'):
            #    if elem.attrib is not None:
            #        location_type = 'plug'
            #for elem in location.iter('thermostat_functionality'):
            #    if elem.attrib is not None:
            #        location_type = 'thermostat'
            
            # Find appliances (if any)
            appliance = location.find('.//appliances/appliance')
            if appliance is not None:
                appliance_id = appliance.attrib['id']

            # Determine location_type from functionality
            if location.find('.//actuator_functionalities/relay_functionality'):
                location_type = 'plug'
            elif location.find('.//actuator_functionalities/thermostat_functionality'):
                location_type = 'thermostat'
            else:
                power_locator='.//logs/point_log[type="electricity_consumed"]'
                if not appliance and location.find(power_locator):
                    p1_ec_log = location.find(power_locator)
                    meter_locator='.//electricity_point_meter'
                    if p1_ec_log.find(meter_locator).get('id'):
                        location_type = 'power'

            if location_name != "Home":
                if location_type == 'plug':
                    location_dict['name'] = location_name
                    location_dict['id'] = appliance_id
                    location_dict['type'] = location_type

                if location_type == 'thermostat':
                    location_dict['name'] = location_name
                    location_dict['id'] = location_id
                    location_dict['type'] = location_type
            # P1
            elif location_type == 'power':
                    location_dict['name'] = location_name
                    location_dict['id'] = location_id
                    location_dict['type'] = location_type
                    
            if location_dict != {}:
                location_list.append(location_dict)
                
        return location_list

    def get_appliance_from_loc_id(self, root, id):
        """Obtains the appliance-data connected to a location - from APPLIANCES."""
        appliances = root.findall('.//appliance')
        appl_list = []
        for appliance in appliances:
            if appliance.find('type') is not None:
                appliance_type = appliance.find('type').text
                
            if appliance.find('description') is not None:
                if 'smart plug' in str(appliance.find('description').text):
                    appliance_type = 'plug'
                    appliance_name = appliance.find('name').text
                    
                if "gateway" not in appliance_type:
                    if appliance.find('location') is not None:
                        appl_location = appliance.find('location').attrib['id']
                        if appl_location == id:
                            appl_dict = {}
                            if (appliance_type == 'zone_thermostat') or (appliance_type == 'thermostatic_radiator_valve') or (appliance_type == 'thermostat'):
                                appl_dict['type'] = appliance_type
                                locator = (".//logs/point_log[type='battery']/period/measurement")
                                appl_dict['battery'] = None
                                if appliance.find(locator) is not None:
                                    battery = appliance.find(locator).text
                                    value = float(battery)
                                    battery = '{:.2f}'.format(round(value, 2))
                                    appl_dict['battery'] = battery
                                locator = (".//logs/point_log[type='thermostat']/period/measurement")
                                appl_dict['setpoint_temp'] = None
                                if appliance.find(locator) is not None:
                                    thermostat = appliance.find(locator).text
                                    thermostat = float(thermostat)
                                    appl_dict['setpoint_temp'] = thermostat
                                locator = (".//logs/point_log[type='temperature']/period/measurement")
                                appl_dict['current_temp'] = None
                                if appliance.find(locator) is not None:
                                    temperature = appliance.find(locator).text
                                    temperature = float(temperature)
                                    appl_dict['current_temp'] = temperature
                                appl_list.append(appl_dict.copy())

        new_list = sorted(appl_list, key=lambda k: k['type'], reverse=True)
        if new_list != []:
            return new_list[0]

    def get_appliance_from_appl_id(self, id):
        """Obtains the appliance-data from appliances without a location - from APPLIANCES."""
        appliance_data = {}
        for appliance in self.get_appliances():
            appliance_name = appliance.find('name').text
            if "Gateway" not in appliance_name:
                appliance_id = appliance.attrib['id']
                if appliance_id == id:
                    appliance_type = appliance.find('type').text
                    appliance_data['type'] = appliance_type
                    boiler_temperature = None
                    locator = (".//logs/point_log[type='boiler_temperature']/period/measurement")
                    if appliance.find(locator) is not None:
                        measurement = appliance.find(locator).text
                        value = float(measurement)
                        boiler_temperature = '{:.1f}'.format(round(value, 1))
                        if boiler_temperature: # new
                            appliance_data['boiler_temp'] = boiler_temperature
                    water_pressure = None
                    locator = (".//logs/point_log[type='central_heater_water_pressure']/period/measurement")
                    if appliance.find(locator) is not None:
                        measurement = appliance.find(locator).text
                        value = float(measurement)
                        water_pressure = '{:.1f}'.format(round(value, 1))
                        if water_pressure: # new
                            appliance_data['water_pressure'] = water_pressure
                    if appliance_type == 'heater_central': # new
                        direct_objects = self.get_direct_objects()
                        appliance_data['boiler_state'] = None
                        locator = (".//logs/point_log[type='boiler_state']/period/measurement")
                        if direct_objects.find(locator) is not None:
                            boiler_state = (direct_objects.find(locator).text == "on")
                            appliance_data['boiler_state'] = boiler_state
                        appliance_data['central_heating_state'] = None
                        locator = (".//logs/point_log[type='central_heating_state']/period/measurement")
                        if direct_objects.find(locator) is not None:
                            central_heating_state = (direct_objects.find(locator).text == "on")
                            appliance_data['central_heating_state'] = central_heating_state
                        appliance_data['cooling_state'] = None
                        locator = (".//logs/point_log[type='cooling_state']/period/measurement")
                        if direct_objects.find(locator) is not None:                      
                            cooling_state = (direct_objects.find(locator).text == "on")
                            appliance_data['cooling_state'] = cooling_state
                        appliance_data['dhw_state'] = None
                        locator = (".//logs/point_log[type='domestic_hot_water_state']/period/measurement")
                        if direct_objects.find(locator) is not None:                      
                            domestic_hot_water_state = (direct_objects.find(locator).text == "on")
                            appliance_data['dhw_state'] = domestic_hot_water_state
                    else:
                        appliance_data['type'] = appliance_type
                        appliance_data['name'] = appliance_name
                        locator = (".//logs/point_log[type='electricity_consumed']/period/measurement")
                        appliance_data['electricity_consumed'] = None
                        if appliance.find(locator) is not None:
                            electricity_consumed = appliance.find(locator).text
                            electricity_consumed = '{:.1f}'.format(round(float(electricity_consumed), 1))
                            appliance_data['electricity_consumed'] = electricity_consumed
                        locator = (".//logs/interval_log[type='electricity_consumed']/period/measurement")
                        appliance_data['electricity_consumed_interval'] = None
                        if appliance.find(locator) is not None:
                            electricity_consumed_interval = appliance.find(locator).text
                            electricity_consumed_interval = '{:.1f}'.format(round(float(electricity_consumed_interval), 1))
                            appliance_data['electricity_consumed_interval'] = electricity_consumed_interval
                        locator = (".//logs/point_log[type='electricity_produced']/period/measurement")
                        appliance_data['electricity_produced'] = None
                        if appliance.find(locator) is not None:
                            electricity_produced = appliance.find(locator).text
                            electricity_produced = '{:.1f}'.format(round(float(electricity_produced), 1))
                            appliance_data['electricity_produced'] = electricity_produced
                        locator = (".//logs/interval_log[type='electricity_produced']/period/measurement")
                        appliance_data['electricity_produced_interval'] = None
                        if appliance.find(locator) is not None:
                            electricity_produced_interval = appliance.find(locator).text
                            electricity_produced_interval = '{:.1f}'.format(round(float(electricity_produced_interval), 1))
                            appliance_data['electricity_produced_interval'] = electricity_produced_interval
                        locator = (".//logs/point_log[type='relay']/period/measurement")
                        appliance_data['relay'] = None
                        if appliance.find(locator) is not None:
                            state = appliance.find(locator).text
                            appliance_data['relay'] = state
     
        if appliance_data != {}:
            return appliance_data

    def get_preset_from_id(self, root, id):
        """Obtains the active preset based on the location_id - from DOMAIN_OBJECTS."""
        for location in root:
            location_id = location.attrib['id']
            if location.find('preset') is not None:
                preset = location.find('preset').text
                if location_id == id:
                    return preset
    
    def get_presets_from_id(self, root, id):
        """Gets the presets from the thermostat based on location_id."""
        rule_ids = {}
        rule_ids = self.get_rule_id_and_zone_location_by_template_tag_with_id(
            root,
            'zone_setpoint_and_state_based_on_preset',
            id,
        )
        if rule_ids is None:
            rule_ids = self.get_rule_id_and_zone_location_by_name_with_id(root, 'Thermostat presets', id)
            if rule_ids is None:
                return None

        presets = {}
        for key,val in rule_ids.items():
            if val == id:
                presets = self.get_preset_dictionary(root, key)
        return presets

    def get_schema_names_from_id(self, root, id):
        """Obtains the available schemas or schedules based on the location_id."""
        rule_ids = {}
        locator = 'zone_preset_based_on_time_and_presence_with_override'
        rule_ids = self.get_rule_id_and_zone_location_by_template_tag_with_id(root, locator, id)
        schemas = {}
        l_schemas = {}
        if rule_ids:
            for key,val in rule_ids.items():
                if val == id:
                    name = root.find("rule[@id='" + key + "']/name").text
                    active = False
                    if root.find("rule[@id='" + key + "']/active").text == 'true':
                        active = True
                    schemas[name] = active
        if schemas != {}:
            return schemas
            
    def get_last_active_schema_name_from_id(self, root, id):
        """Determine the last active schema."""
        epoch = datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)
        date_format = "%Y-%m-%dT%H:%M:%S.%f%z"
        rule_ids = {}
        locator = 'zone_preset_based_on_time_and_presence_with_override'
        rule_ids = self.get_rule_id_and_zone_location_by_template_tag_with_id(root, locator, id)
        schemas = {}
        if rule_ids:
            for key,val in rule_ids.items():
                if val == id:
                    schema_name = root.find("rule[@id='" + key + "']/name").text
                    schema_date = root.find("rule[@id='" + key + "']/modified_date").text
                    schema_time = parse(schema_date)
                    schemas[schema_name] = (schema_time - epoch).total_seconds()
                last_modified = sorted(schemas.items(), key=lambda kv: kv[1])[-1][0]
                return last_modified

    @staticmethod
    def get_rule_id_and_zone_location_by_template_tag_with_id(root, rule_name, id):
        """Obtains the rule_id based on the given template_tag and location_id."""
        schema_ids = {}
        rules = root.findall('.//rule')
        for rule in rules:
            try:
                name = rule.find('template').attrib['tag']
            except KeyError:
                name = None
            if (name == rule_name):
                rule_id = rule.attrib['id']
                for elem in rule.iter('location'):
                    if elem.attrib is not None:
                        location_id = elem.attrib['id']
                        if location_id == id:
                            schema_ids[rule_id] = location_id
        if schema_ids != {}:
            return schema_ids

    def get_rule_id_and_zone_location_by_name_with_id(self, root, rule_name, id):
        """Obtains the rule_id and location_id based on the given name and location_id."""
        schema_ids = {}
        rules = root.findall('.//rule')
        for rule in rules:
            try:
                name = rule.find('name').text
            except AttributeError:
                name = None
            if (name == rule_name):
                rule_id = rule.attrib['id']
                for elem in rule.iter('location'):
                    if elem.attrib is not None:
                        location_id = elem.attrib['id']
                        if location_id == id:
                            schema_ids[rule_id] = location_id
        if schema_ids != {}:
            return schema_ids

    def get_outdoor_temperature(self, root):
        """Obtains the outdoor_temperature from the thermostat."""
        locator = (".//logs/point_log[type='outdoor_temperature']/period/measurement")
        if root.find(locator) is not None:
            measurement = root.find(locator).text
            value = float(measurement)
            value = '{:.1f}'.format(round(value, 1))
            return value

    def get_illuminance(self, root):
        """Obtain the illuminance value from the thermostat."""
        locator = (".//logs/point_log[type='illuminance']/period/measurement")
        if root.find(locator) is not None:
            measurement = root.find(locator).text
            value = float(measurement)
            value = '{:.1f}'.format(round(value, 1))
            return value

    @staticmethod
    def get_preset_dictionary(root, rule_id):
        """Obtains the presets from a rule based on rule_id."""
        preset_dictionary = {}
        directives = root.find(
            "rule[@id='" + rule_id + "']/directives"
        )
        for directive in directives:
            preset = directive.find("then").attrib
            keys, values = zip(*preset.items())
            if str(keys[0]) == 'setpoint':
                preset_dictionary[directive.attrib["preset"]] = [float(preset["setpoint"]), 0]
            else:
                preset_dictionary[directive.attrib["preset"]] = [float(preset["heating_setpoint"]), float(preset["cooling_setpoint"])]
        if preset_dictionary != {}:
            return preset_dictionary
            
    def _set_schema_state(self, root, loc_id, name, state):
        """Sets the schedule, helper-function."""
        schema_rule_ids = {}
        schema_rule_ids = self.get_rule_id_and_zone_location_by_name_with_id(root, str(name), loc_id)
        for schema_rule_id,location_id in schema_rule_ids.items():
            if location_id == loc_id:
                templates = root.findall(".//*[@id='{}']/template".format(schema_rule_id))
                template_id = None
                for rule in templates:
                    template_id = rule.attrib['id']

                uri = '{};id={}'.format(RULES, schema_rule_id)

                state = str(state)
                data = '<rules><rule id="{}"><name><![CDATA[{}]]></name>' \
                       '<template id="{}" /><active>{}</active></rule>' \
                       '</rules>'.format(schema_rule_id, name, template_id, state)

                xml = requests.put(
                      self._endpoint + uri,
                      auth=(self._username, self._password),
                      data=data,
                      headers={'Content-Type': 'text/xml'},
                      timeout=10
                )

                if xml.status_code != requests.codes.ok: # pylint: disable=no-member
                    CouldNotSetTemperatureException("Could not set the schema to {}.".format(state) + xml.text)
                return '{} {}'.format(xml.text, data)

    def _set_preset(self, location_id, loc_type, preset):
        """Sets the preset, helper function."""
        locations_root = self.get_locations()
        current_location = locations_root.find("location[@id='" + location_id + "']")
        location_name = current_location.find('name').text
        location_type = current_location.find('type').text

        xml = requests.put(
                self._endpoint
                + LOCATIONS
                + ";id="
                + location_id,
                auth=(self._username, self._password),
                data="<locations>"
                + '<location id="'
                + location_id
                + '">'
                + "<name>"
                + location_name
                + "</name>"
                + "<type>"
                + location_type
                + "</type>"
                + "<preset>"
                + preset
                + "</preset>"
                + "</location>"
                + "</locations>",
                headers={"Content-Type": "text/xml"},
                timeout=10,
            )
        if xml.status_code != requests.codes.ok: # pylint: disable=no-member
            raise CouldNotSetPresetException("Could not set the given preset: " + xml.text)
        return xml.text

    def _set_temp(self, root, loc_id, loc_type, temperature):
        """Sends a temperature-set request, helper function."""
        uri = self.__get_temperature_uri(root, loc_id, loc_type)
        temperature = str(temperature)

        if uri is not None:
            xml = requests.put(
                self._endpoint + uri,
                auth=(self._username, self._password),
                data="<thermostat_functionality><setpoint>" + temperature + "</setpoint></thermostat_functionality>",
                headers={"Content-Type": "text/xml"},
                timeout=10,
            )

            if xml.status_code != requests.codes.ok: # pylint: disable=no-member
                CouldNotSetTemperatureException("Could not set the temperature." + xml.text)
            return xml.text
        else:
            CouldNotSetTemperatureException("Could not obtain the temperature_uri.")

    def __get_temperature_uri(self, root, loc_id, loc_type):
        """Determine the location-set_temperature uri - from DOMAIN_OBJECTS."""
        locator = (
            "location[@id='"
            + loc_id
            + "']/actuator_functionalities/thermostat_functionality"
        )
        thermostat_functionality_id = root.find(locator).attrib['id']
        
        temperature_uri = (
            LOCATIONS
            + ";id="
            + loc_id
            + "/thermostat;id="
            + thermostat_functionality_id
        )
        
        return temperature_uri
        
    def set_relay_state(self, root, appl_id, type, state):
        """Switch the Plug to off/on."""
        locator = ("appliance[type='" + type + "']/actuator_functionalities/relay_functionality")
        relay_functionality_id = root.find(locator).attrib['id']
        uri = (
            APPLIANCES
            + ";id="
            + appl_id
            + "/relay;id="
            + relay_functionality_id
        )

        state = str(state)

        if uri is not None:
            xml = requests.put(
                self._endpoint + uri,
                auth=(self._username, self._password),
                data="<relay_functionality><state>" + state + "</state></relay_functionality>",
                headers={"Content-Type": "text/xml"},
                timeout=10,
            )

            if xml.status_code != requests.codes.ok: # pylint: disable=no-member
                print("Could not set the relay state." + xml.text)
            return xml.text
        else:
            CouldNotSetTemperatureException("Could not obtain the relay_uri.")


class PlugwiseException(Exception):
    """Define Exceptions."""

    def __init__(self, arg1, arg2=None):
        """Set the base exception for interaction with the Plugwise gateway"""
        self.arg1 = arg1
        self.arg2 = arg2
        super(PlugwiseException, self).__init__(arg1)


class RuleIdNotFoundException(PlugwiseException):
    """
    Raise an exception for when the rule_id is not found in the direct objects
    """

    pass


class CouldNotSetPresetException(PlugwiseException):
    """Raise an exception for when the preset could  not be set"""

    pass
    
    
class CouldNotSetTemperatureException(PlugwiseException):
    """Raise an exception for when the temperature could not be set."""

    pass