"""Plugwise Home Assistant component."""
import requests
import datetime
import pytz
import xml.etree.cElementTree as Etree

# For python 3.6 strptime fix
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
        self._endpoint = "http://" + host + ":" + str(port)

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
        """Provide the devices-names and application IDs."""
        appliances = self.get_appliances()
        locations = self.get_locations()
        domain_objects = self.get_domain_objects()
        appl_dict = self.get_appliance_dictionary(appliances)
        dups = self.find_duplicate_location_ids(appliances)
        
        i = 0
        keys = ['name','id']
        devices = []
        for id,type in appl_dict.items():
            user_name = self.get_user_names_dictionary_from_id(locations, id)
            device = []
            if user_name:
                for key,val in user_name.items():
                    if dups:
                        if key in dups:
                            i += 1
                    if i != 2:
                        real_user_name = self.get_real_user_name_and_data_from_id(domain_objects, key)
                        if real_user_name:
                            for user_name,data in real_user_name.items():
                                device.append(user_name)
                                device.append(id)
                    else:
                        i -= 1
            else:
                device.append('Controlled Device')
                device.append(id)
            if device != []:
                devices.append(device)

        data = [{k:v for k,v in zip(keys, n)} for n in devices]

        for items in data:
            if items['name'] == 'Controlled Device':
                front_item = items

        new_data = self.rearrange(data, front_item)
        return new_data

    @staticmethod
    def rearrange(arg,item):
        predefined_list = [item]
        rest_list = []
        to_move_to_front = []

        for item in arg:
            if item not in predefined_list:
                rest_list.append(item)
            else:
                to_move_to_front.append(item)

        to_move_to_front.extend(rest_list)

        return to_move_to_front

    def get_device_data(self, id, ctrl_id):
        """Provide the device-data from the application ID."""
        appliances = self.get_appliances()
        locations = self.get_locations()
        domain_objects = self.get_domain_objects()
        appl_dict = self.get_appliance_dictionary(appliances)
        outdoor_temp = self.get_outdoor_temperature(locations)
        pressure = self.get_water_pressure(appliances)
        dups = self.find_duplicate_location_ids(appliances)

        i = 0
        data = {}
        for appl_id,appl_type in appl_dict.items():
            if appl_id == id:
                user_name = self.get_user_names_dictionary_from_id(locations, appl_id)
                if user_name:
                    for key,val in user_name.items():
                        if dups:
                            if key in dups:
                                i += 1
                        if i != 2:
                            real_user_name = self.get_real_user_name_and_data_from_id(domain_objects, key)
                            if real_user_name:
                                for k,v in real_user_name.items():
                                    data['batt status'] = appl_type[1]
                                    data['active preset'] = v[0]
                                    data['setpoint temp'] = v[1]
                                    data['current temp'] = v[2]
                                    presets = self.get_presets_from_id(domain_objects, key)
                                    data['presets'] = presets
                                    schemas = self.get_schema_names_from_id(domain_objects, key)
                                    a_sch = []
                                    l_sch = None
                                    s_sch = None
                                    if schemas:
                                        for a,b in schemas.items():
                                            if a != "Last":
                                                a_sch.append(a)
                                            else:
                                                l_sch = b
                                            if b == True:
                                                s_sch = a
                                    data['available schedules'] = a_sch
                                    data['selected schedule'] = s_sch
                                    data['last used'] = l_sch
                        else:
                            i -= 1
            if appl_id == ctrl_id:
                data['boiler state'] = appl_type[1]
                data['central heating state'] = appl_type[2]
                data['cooling state'] = appl_type[3]
                data['domestic hot water state']= appl_type[4]
            
        return data
    
    def get_appliances(self):
        """Collect the appliances XML-data."""
        xml = requests.get(
              self._endpoint + APPLIANCES,
              auth=(self._username, self._password),
              timeout=10,
        )
        if xml.status_code != requests.codes.ok:
            raise ConnectionError("Could not get the appliances.")
        return Etree.fromstring(self.escape_illegal_xml_characters(xml.text))

    def get_locations(self):
        """Collect the locations XML-data."""
        xml = requests.get(
              self._endpoint + LOCATIONS,
              auth=(self._username, self._password),
              timeout=10,
        )
        if xml.status_code != requests.codes.ok:
            raise ConnectionError("Could not get the appliances.")
        return Etree.fromstring(self.escape_illegal_xml_characters(xml.text))

    def get_direct_objects(self):
        """Collect the direct_objects XML-data."""
        xml = requests.get(
              self._endpoint + DIRECT_OBJECTS,
              auth=(self._username, self._password),
              timeout=10,
        )
        if xml.status_code != requests.codes.ok:
            raise ConnectionError("Could not get the direct objects.")
        return Etree.fromstring(self.escape_illegal_xml_characters(xml.text))
    
    def get_domain_objects(self):
        """Collect the domain_objects XML-data."""
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
        """Replace illegal &-character."""
        return re.sub(r'&([^a-zA-Z#])',r'&amp;\1',root)
    
    def get_appliance_dictionary(self, root):
        """Obtains the existing appliance types and ids - from APPLIANCES."""
        appliance_dictionary = {}
        for appliance in root:
            appliance_name = appliance.find("name").text
            if "Gateway" not in appliance_name:
                appliance_id = appliance.attrib["id"]
                appliance_type = appliance.find("type").text
                if appliance_type != "heater_central":
                    locator = (".//logs/point_log[type='battery']/period/measurement")
                    battery = None
                    if appliance.find(locator) is not None:
                        battery = appliance.find(locator).text
                    appliance_dictionary[appliance_id] = (appliance_type, battery)
                else:
                    boiler_temperature = None
                    locator = (".//logs/point_log[type='boiler_temperature']/period/measurement")
                    if appliance.find(locator) is not None:
                        measurement = appliance.find(locator).text
                        value = float(measurement)
                        boiler_temperature = '{:.1f}'.format(round(value, 1))
                    locator = (".//logs/point_log[type='boiler_state']/period/measurement")
                    boiler_state =  None
                    if appliance.find(locator) is not None:
                        boiler_state = (appliance.find(locator).text == "on")
                    locator = (".//logs/point_log[type='central_heating_state']/period/measurement")
                    central_heating_state = None
                    if appliance.find(locator) is not None:
                        central_heating_state = (appliance.find(locator).text == "on")
                    locator = (".//logs/point_log[type='cooling_state']/period/measurement")
                    cooling_state =  None
                    if appliance.find(locator) is not None:                      
                        cooling_state = (appliance.find(locator).text == "on")
                    locator = (".//logs/point_log[type='domestic_hot_water_state']/period/measurement")
                    domestic_hot_water_state =  None
                    if appliance.find(locator) is not None:                      
                        domestic_hot_water_state = (appliance.find(locator).text == "on")                    
                    appliance_dictionary[appliance_id] = (
                        boiler_temperature, boiler_state,
                        central_heating_state, cooling_state,
                        domestic_hot_water_state
                        )
                
        return appliance_dictionary

    def find_duplicate_location_ids(self, root):
        """Obtains the existing appliance types and looks for duplicate location IDs."""
        appliances = root.findall(".//appliance")
        ids = []
        dups = []
        for appliance in appliances:
            appliance_name = appliance.find("name").text
            if "Gateway" not in appliance_name:
                appl_loc_id = appliance.find('location')
                if appl_loc_id is not None:
                    loc_id = appl_loc_id.attrib["id"]
                    ids.append(loc_id)
        dups = [ids[i] for i in range(len(ids)) if not i == ids.index(ids[i])]
        return dups

    def get_user_names_dictionary_from_id(self, root, id):
        """Obtains the system names from the appliance id - from LOCATIONS."""
        user_names_dictionary = {}
        locations = root.findall(".//location")
        for location in locations:
            location_name = location.find("name").text
            location_id = location.attrib["id"]
            for appliance in location.iter('appliance'):
                if appliance.attrib is not None:
                    appliance_id = appliance.attrib["id"]
                if appliance_id == id:
                    user_names_dictionary[location_id] = location_name

        return user_names_dictionary

    def get_real_user_name_and_data_from_id(self, root, id):
        """Obtains the name given by the user and the related data from the appliance id - from DOMAIN_OBJECTS."""
        real_data = {}
        current_location = root.find("location[@id='" + id + "']")
        if current_location.find("name") is not None:
            location_name = current_location.find("name").text
        preset = current_location.find("preset").text
        setpoint = current_location.find(".//logs/point_log[type='thermostat']/period/measurement").text
        if setpoint:
                setp_val = float(setpoint)        
        temperature = current_location.find(".//logs/point_log[type='temperature']/period/measurement").text
        if temperature:
                temp_val = float(temperature)
        real_data[location_name] = (preset, setp_val, temp_val)

        return real_data
    
    def get_presets_from_id(self, root, id):
        """Gets the presets from the thermostat based on location_id"""
        rule_ids = {}
        rule_ids = self.get_rule_id_and_zone_location_by_template_tag(
            root,
            "zone_setpoint_and_state_based_on_preset",
        )
        
        if rule_ids is None:
            rule_ids = self.get_rule_id_and_zone_location_by_name(
                root, "Thermostat presets"
            )
            if rule_ids is None:
                raise RuleIdNotFoundException("Could not find the rule ids.")

        for key,val in rule_ids.items():
            if val == id:
                presets = self.get_preset_dictionary(root, key)
        return presets

    def get_schema_names_from_id(self, root, id):
        """Obtain the available schemas or schedules for a location ID ."""
        epoch = datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)
        date_format = "%Y-%m-%dT%H:%M:%S.%f%z"
        schema_names = {}
        locator = "zone_preset_based_on_time_and_presence_with_override"
        schema_names = self.get_rule_id_and_zone_location_by_template_tag(root, locator)
        schemas = {}
        l_schemas = {}
        if schema_names:
            for key,val in schema_names.items():
                if val == id:
                    name = root.find("rule[@id='" + key + "']/name").text
                    active = False
                    if root.find("rule[@id='" + key + "']/active").text == 'true':
                        active = True
                    schemas[name] = active
                    date = root.find("rule[@id='" + key + "']/modified_date").text
                    # Python 3.6 fix (%z %Z issue)
                    corrected = re.sub(r"([-+]\d{2}):(\d{2})(?:(\d{2}))?$", r"\1\2\3", date)
                    time = datetime.datetime.strptime(corrected, date_format)
                    l_schemas[name] = (time - epoch).total_seconds()
            if l_schemas:
                last_modified = sorted(schemas.items(), key=lambda kv: kv[1])[-1][0]
                schemas['Last'] = last_modified
        if schemas != {}:
            return schemas

    @staticmethod
    def get_rule_id_and_zone_location_by_template_tag(root, rule_name):
        """Gets the rule ID based on template_tag"""
        schema_ids = {}
        name = None
        rules = root.findall("rule")
        for rule in rules:
            name = rule.find("template").attrib["tag"]
            if name:
                if (name == rule_name):
                    rule_id = rule.attrib["id"]
                    for elem in rule.iter("location"):
                        location_id = elem.attrib["id"]
                        schema_ids[rule_id] = location_id
        if schema_ids != {}:
            return schema_ids

    def get_outdoor_temperature(self, root):
        """Obtains the outdoor_temperature from the thermostat."""
        locations = root.findall(".//location")
        for location in locations:
            locator = (".//logs/point_log[type='outdoor_temperature']/period/measurement")
            if location.find(locator) is not None:
                measurement = location.find(locator).text
                value = float(measurement)
                value = '{:.1f}'.format(round(value, 1))
                return value

    def get_water_pressure(self, root):
        """Obtains the water pressure value from the thermostat"""
        appliances = root.findall(".//appliance")
        for appliance in appliances:
            locator = (".//logs/point_log[type='central_heater_water_pressure']/period/measurement")
            if appliance.find(locator) is not None:
                measurement = appliance.find(locator).text
                value = float(measurement)
                value = '{:.1f}'.format(round(value, 1))
                return value
        return None

    @staticmethod
    def get_measurement_from_point_log(root, point_log_id):
        """Gets the measurement from a point log based on point log ID"""
        locator = (
            "*/logs/point_log[@id='"
            + point_log_id
            + "']/period/measurement"
        )
        if root.find(locator):
            return root.find(locator).text

    def get_rule_id_and_zone_location_by_name(self, root, rule_name):
        """Gets the rule ID and location ID based on name"""
        schema_ids = {}
        loation = None
        rules = root.findall("rule")
        for rule in rules:
            if rule.find("name").text == rule_name:
                rule_id = rule.attrib["id"]
                for elem in rule.iter("location"):
                    if elem.attrib is not None:
                        location_id = elem.attrib["id"]
                        schema_ids[rule_id] = location_id
        if schema_ids != {}:
            return schema_ids

    @staticmethod
    def get_preset_dictionary(root, rule_id):
        """
        Gets the presets from a rule based on rule ID and returns a dictionary
        with all the key-value pairs
        """
        preset_dictionary = {}
        directives = root.find(
            "rule[@id='" + rule_id + "']/directives"
        )
        for directive in directives:
            preset = directive.find("then").attrib
            keys, values = zip(*preset.items())
            if str(keys[0]) == 'setpoint':
                preset_dictionary[directive.attrib["preset"]] = float(preset["setpoint"])
            else:
                preset_dictionary[directive.attrib["preset"]] = float(preset["heating_setpoint"])                
        if preset_dictionary != {}:
            return preset_dictionary

####################
# Setting stuff... #
####################

    def set_schema_state(self, root, loc_id, schema, state):
        """Sends a set request to the location-schema with the given name - domain_objects"""
        schema_rule_ids = {}
        schema_rule_ids = self.get_rule_id_and_zone_location_by_name(root, str(schema))
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
                       '</rules>'.format(schema_rule_id, schema, template_id, state)

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

    def set_preset(self, root, loc_id, preset):
        """Sets the given location-preset on the thermostat - domain_objects"""
        location_ids = []
        locator = ("appliance[type='thermostat']/location")
        location_ids = root.find(locator).attrib["id"]
        for location_id in location_ids:
            if location_id == loc_id:
                locations_root = self.get_locations()
                current_location = locations_root.find("location[@id='" + location_id + "']")
                location_name = current_location.find("name").text
                location_type = current_location.find("type").text

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

    def set_temperature(self, root, loc_id, temperature):
        """Sends a set request to the thermostat with the given temperature - domain_objects."""
        uri = self.__get_temperature_uri(root, loc_id)

        temperature = str(temperature)

        xml = requests.put(
              self._endpoint + uri,
              auth=(self._username, self._password),
              data="<thermostat_functionality><setpoint>"
              + temperature
              + "</setpoint></thermostat_functionality>",
              headers={"Content-Type": "text/xml"},
              timeout=10,
        )

        if xml.status_code != requests.codes.ok: # pylint: disable=no-member
            CouldNotSetTemperatureException("Could not set the temperature." + xml.text)
        return xml.text

    def __get_temperature_uri(self, loc_id, root):
        """Determine the location-set_temperature uri - domain_objects."""
        location_ids = []
        locator = ("appliance[type='thermostat']/location")
        location_ids = root.find(locator).attrib["id"]
        for location_id in location_ids:
            if location_id == loc_id:
                locator = (
                    "location[@id='"
                    + location_id
                    + "']/actuator_functionalities/thermostat_functionality"
                )
                thermostat_functionality_id = root.find(locator).attrib["id"]
                temperature_uri = (
                    LOCATIONS
                    + ";id="
                    + location_id
                    + "/thermostat;id="
                    + thermostat_functionality_id
                )
                return temperature_uri


class PlugwiseException(Exception):
    """Define Exceptions."""

    
    def __init__(self, arg1, arg2=None):
        """Set the base exception for interaction with the Plugwsise gateway"""
        self.arg1 = arg1
        self.arg2 = arg2
        super(PlugwiseException, self).__init__(arg1)


class RuleIdNotFoundException(PlugwiseException):
    """
    Raise an exception for when the rule id is not found in the direct objects
    """

    pass


class CouldNotSetPresetException(PlugwiseException):
    """Raise an exception for when the preset can not be set"""

    pass


class CouldNotSetTemperatureException(PlugwiseException):
    """Raise an exception for when the temperature could not be set"""

    pass
