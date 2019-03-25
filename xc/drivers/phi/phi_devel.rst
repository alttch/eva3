Developing own PHI (Physical Interface) for EVA ICS. HOWTO
**********************************************************

PHI (Physical interface) is a low level driver which communicates directly with
an equipment. PHI should not contain any logic, its job is only to get/set an
equipment to the state requested by LPI.

Required variables in a header
==============================

PHI info
--------

* **__author__**        module author
* **__copyright__**     copyright
* **__license__**       module license
* **__version__**       module version
* **__description__**   module description (keep it short)


PHI system info
---------------

the next fields are processed by controller, so make them exactly as required

* **__equipment__**     supported equipment (list or string)
* **__api__**           module API (integer number), current is **4**

* **__required__**      features required from LPI (Logical to Physical
  Interface, list):

 * **port_get** get single port data
 * **port_set** set single port data
 * **aao_get** get and process all ports at once
 * **aao_set** set all ports at once
 * **status** process item status
 * **value** process item values
 * **action** unit actions

* **__mods_required__** required python modules (not included neither in
  standard Python install nor in EVA ICS)

* **__lpi_default__** if specified, the default driver will be created for this
  PHI when loaded.

* **__features__**      own features provided (list):

 * **port_get** get single port data
 * **port_set** set single port data
 * **aao_get** get all ports at once (if no port is specified)
 * **aao_set** set all ports at once (if list of ports and
   list of data is given)
 * **universal** PHI is universal and process **cfg** in requests.
 * **cache** PHI supports state caching (useful for slow devices)

PHI help
--------

Each PHI module should contain 4 help variables:

* **__config__help__** module configuration help (on load)
* **__get_help__** additional configuration params possible for LPI to send
  with **get** command
* **__set_help__** additional configuration params possible for LPI to send
  with **set** command

First variable should be human readable, others may copy, join or process the
first one or each other in any way.

All variables should be in list format, containing dictionaries with the
following context:

* **name** property name
* **help** property description (help)
* **type** property type
* **required** *True* if property is required, *False* if it's optional

Property **type** may be:

* **bool** boolean (True/False)
* **str** string
* **url** string containing url
* **int** integer
* **uint** unsigned integer (greater or equal to 0)
* **hex** hexadecimal number
* **bin** binary number
* **float** float number
* **ufloat** unsigned float (greater or equal to 0)
* **list:type** list of variables with type specified
* **enum:type:a,b,c** list of the permitted specified type values

If the property accepts multiple types, they should be listed via *or* (**|**)
symbol.

The last one variable is

* **__help__**

It should contain the extended PHI description and operation manual. May be in
any variable format and use restructured text directives for formatting.

Classes and modules
===================

It's allowed to import any Python system module or module installed by EVA ICS.
If PHI requires installing more modules, they should be listed in PHI help file
and in **__mods_required__** variable.

.. warning::

    All non-standard modules (not included neither in Python install nor in EVA
    ICS) should be imported with try/catch with **importlib**, their
    unavailability shouldn't block loading PHI for informational puproses.

Importing modules **eva.uc.drivers.tools**, **eva.tools**, **eva.traphandler**,
**eva.uc.modbus**, **eva.uc.smbus** and functions from
**eva.uc.driverapi**:

* **get_version()** get Driver API version
* **get_polldelay()** get EVA poll delay
* **get_timeout()** get default timeout
* **critical()** send EVA critical call
* **log_traceback()** log traceback debug info
* **lock(l, timeout, expires)** acquire lock "eva:phi:**l**", wait max
  **timeout** sec, lock automatically expires in **expires** sec. Timeout and
  expiration time can't be longer than default controller timeout.
* **unlock(l)** release lock "eva:phi:**l**"
* **handle_phi_event(phi, port, data)** ask Driver API to handle event (see
  below)

is highly welcome. Importing other EVA modules or driverapi functions is not
recommended unless you really know what you do.

The main class is defined as:

.. code-block:: python

    from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
    from eva.uc.driverapi import phi_constructor

    class PHI(GenericPHI):
        #<your code>

Constructor
===========

The constructor should set the above constants to class variables to let them
be serialized by parent class if requested:

.. code-block:: python

    @phi_constructor
    def __init__(self, **kwargs):
        # your code, e.g. parsing self.phi_cfg

Decorator *@phi_constructor* automatically invokes parent constructor and
handles special init requests.

If the constructor faces a problem (e.g. parsing a config or checking
equipment, e.g. local bus) it may set *self.ready=False* to abort controller
loading the module.

If PHI methods get/set can't work with single ports at all (e.g. equipment
returns state of all ports at once only), constructor should set variables:

* **self.aao_get=True** tells LPI the returned with PHI.get method data will
  always contain all port states even if the port is specified in **get**.
* **self.aao_set=True** asks LPI to collect as much data to set as possible, and
  then call PHI **set** method

The parent constructor sets the variable **self.phi_cfg** to phi_cfg or to {},
so it's safe to work with it with *self.phi_cfg.get(cfgvar)*.

Primary methods
===============

The following methods should be defined. **cfg** param may contain
configuration params which should override the default ones for the current
call.

.. code-block:: python

    # if PHI can read data from the equipment
    def get(self, port=None, cfg=None, timeout=0):
        #<your code>
        #should return a single state value or a dict { 'port': value }
        #port should always be a string
        #
        #should return None if failed, integer for status, string for values
        #
        #if PHI supports aao_get feature, it should return all port states when
        #no port is specified in request.
    
    # if PHI can write data to the equipment
    def set(self, port=None, data=None, cfg=None, timeout=0):
        #<your code>
        #should return True (or result) if passed, False or None if failed
        #
        #If PHI supports aao_set feature, it should deal with a list of ports,
        #if no - with a single port only. If both port_set and aao_set are
        #specified in features, PHI should deal with both single port and list
        #of ports

**port** and **data** may be integers, string, contain lists or be set as None.
PHI should always be ready to any incoming params and handle the missing or
incorrect by itself. If **port** contains a list, **data** always contain a
list too.

**cfg** may contain equipment configuration options. If the driver is
universal, it should handle them properly.

.. warning::

    watch out for the timeout - if it's expired, the controller may crash or be
    forcedly restarted.  Always calculate the remaining time for the external
    calls and return error as soon as it comes closer to expiration.

Method **test** should perform a self-test (equipment test) if cmd=='self',
other methods are variable and may be used e.g. for debugging. If command is
not understood by the method, it's a rule of good taste to return a help text
(dict *{ 'command': 'command help' }*).

.. code-block:: python

    def test(self, cmd=None):
        #<your code>

Method **exec** may be implemented to perform some actions on the equipment,
e.g. changing the equipment settings or manage the firmware. You can implement
any commands in any form you wish using **cmd** and **args** params.

.. code-block:: python

    def exec(self, cmd=None, args=None):
        #<your code>

The method should be used for real commands only, all the tests (e.g. testing
**get** method, obtaining equipment info for testing or informational purposes)
should be implemented in **test**. After the command execution, the method
should return *OK* on success or *FAILED* on failure. If command is not
understood by the method, it's a rule of good taste to return a help text (dict
*{ 'command': 'command help' }*).

The following methods may be used to call or register/unregister anything on
driver load/unload:

.. code-block:: python

    def start(self):
        #<your code>

    def stop(self):
        #<your code>


Parent methods
==============

Parent class provides the following useful functions:

* **self.set_cached_state(data)** set driver cached state (any format)
* **self.get_cached_state()** return the state cached before. If the cache is
  expired (self.cache param handled by parent), the method return None

All the logging should be done with the following methods:

* **self.log_debug(msg)**
* **self.log_info(msg)**
* **self.log_warning(msg)**
* **self.log_error(msg)**
* **self.log_critical(msg)**
* **self.critical(msg)**

The last two methods do the same, logging an event and calling controller
critical() method.

Handling events
===============

If the equipment sends any event, PHI should ask Driver API to handle it. This
can be done with method

.. code-block:: python

    eva.uc.driverapi.handle_phi_event(phi, port, data)

where:

* **phi** = **self**
* **port** = port, where the event has happened
* **data** = port state values, as much as possible (dict *{'port': state }*)

The controller will call update() method for all items using the caller PHI for
updating, providing LPIs state data to let them process the event with
minimized amount of additional PHI.get() calls.

Value *-1* can be used to set unit error status, value *False* to set sensor
error status.

Handling SNMP traps
-------------------

First you need to subscribe to EVA trap handler. Import **eva.traphandler** mod
and modify PHI start and stop methods:

.. code-block:: python

    import eva.traphandler

    class PHI(GenericPHI):

        # class code

        def start(self):
            #<your code>
            eva.traphandler.subscribe(self)

        def stop(self):
            #<your code>
            eva.traphandler.unsubscribe(self)

EVA trap handler calls method **process_snmp_trap(data)** for each object
subscribed, so let's create it inside a primary class:

.. code-block:: python

    def process_snmp_trap(self, host, data):
        #<your code>

**host** IP address of the host where SNMP trap is coming from.

**data** a dict with name/value pairs, where name is SNMP numeric OID without a
first dot, and value is always a string. Check if this trap belongs to your
device and perform the required actions. Don't worry about the timeout (except
for the actual reaction time on a trap event) because every method is being
executed in its own thread.

EVA traphandler doesn't care about the method return value and you must process
all the errors by yourself.

Schedule events
---------------

If the equipment doesn't send any events, PHI can initiate updating the items
by itself. To perform this, PHI should support **aao_get** feature and be
loaded with *update=N* config param. Updates, intervals as well as the whole
update process are handled by parent class.

Working with I2C/SMBus
======================

It's highly recommended to use internal UC locking for I2C bus. Then you can
use any module available to work with I2C/SMBus. As there are a lot of modules
with similar functions, you can choose it on your own. See the code example
below:

.. code-block:: python

    # ...........
    # we'll use smbus2 module in this example
    __mods_required__ = ['smbus2']
    # ...........
    # import i2c locker module
    import eva.uc.i2cbus

    def __init__(self, phi_cfg=None, info_only=False):
        # code
        try:
            self.smbus2 = importlib.import_module('smbus2')
        except:
            self.log_error('unable to load smbus2 python module')
            self.ready = False
            return

    def get(self, port=None, cfg=None, timeout=0):
        if not eva.uc.i2cbus.lock(self.bus):
            self.log_error('unable to lock I2C bus')
            return None
        bus = self.smbus2.SMBus(self.bus)
        # perform some operations, then release the bus for other threads
        eva.i2cbus.release(self.bus)
        return result

All I2C/SMBus exceptions, timeouts and retries should be handled by the code of
your PHI.

Working with ModBus
===================

Working with ModBus is pretty easy. PHIs don't need to care about the ModBus
connection and data exchange at all, everything is managed by **eva.uc.modbus**
module.

.. code-block:: python

    # everything you need is just import module
    import eva.uc.modbus as modbus

    def __init__(self, phi_cfg=None, info_only=False):
        # ....
        # it's recommended to force aao_get in ModBus PHI to let it read states
        # with one modbus request
        self.aao_get = True
        self.modbus_port = self.phi_cfg.get('port')
        # check in constructor if the specified modbus port is defined
        if not modbus.is_port(self.modbus_port):
            self.log_error('modbus port ID not specified or invalid')
            self.ready = False
            return
        # store unit id PHI is loaded for
        try:
            self.unit_id = int(self.phi_cfg.get('unit'))
        except:
            self.ready = False
            return

    def get(self, port=None, cfg=None, timeout=0):
        # modbus.get_port(port_id) function returns:
        # False - if port failed to connect,
        # None - if port doesn't exist or may exceed the timeout,
        # 0 - if port is locked and busy,
        # or the port object itself
        mb = modbus.get_port(self.modbus_port, timeout)
        if not mb: return None
        # The port object is a regular pymodbus object
        # (https://pymodbus.readthedocs.io) and supports all pymodbus functions.
        # All the functions are wrapped with EVA modbus module which handles
        # all errors and retry attempts. The ports PHI gets are always in the
        # connected state.
        r = mb.read_coils(0, 16, unit=self.unit_id)
        # Release modbus port as soon as possible to let other components work
        # with it while your PHI is processing the data
        mb.release()
        # result is a regular pymodbus result
        if rr.isError(): return None
        # let's convert 16 coils to 16 port states
        result = {}
        try:
            for i in range(16):
                result[str(i + 1)] = 1 if rr.bits[i] else 0
        except:
            result = None
        return result


The variable **client_type** of the port object (*mb.client_type*) holds the
port type (tcp, udp, rtu, ascii or binary). This can be used to make PHI
work with the equipment of the same type which uses e.g. different registers
for different connection types.

Working with 1-wire via OWFS
============================

As EVA ICS has virtual OWFS buses, you don't need to initialize OWFS by
yourself.

Methods available:

* **owfs.is_bus(bus_id)** returns *True* if bus is defined
* **bus = owfs.get_bus(bus_id)** get bus. If locking is defined, the bus becomes
  exclusively locked.
* **bus.read(path, attr)** read equipment attribute value
* **bus.write(path, attr, value)** write equipment attribute value
* **bus.release()** Release bus. As bus may be locked for others, the method
  should be always called immediately after the work with bus is finished.

*read(path, attr)* and *write(path, attr,
value*).

.. code-block:: python

    # everything you need is just import module
    import eva.uc.owfs as owfs

    def __init__(self, phi_cfg=None, info_only=False):
        # ....
        # it's recommended to force aao_get in ModBus PHI to let it read states
        # with one modbus request
        self.owfs_bus = self.phi_cfg.get('owfs')
        # check in constructor if the specified modbus port is defined
        if not owfs.is_bus(self.owfs_bus):
            self.log_error('owfs bus ID not specified or invalid')
            self.ready = False
            return
        # store path of equipment PHI is loaded for
        self.path = self.phi_cfg.get('path')
        if not self.path:
            self.log_error('owfs path is not specified')
            self.ready = False
            return

    def get(self, port=None, cfg=None, timeout=0):
        bus = owfs.get_bus(self.owfs_bus)
        if not bus: return None
        try:
            value = us.read(path, 'temperature')
            if not value:
                raise Exception('can not obtain temperature value')
            return {'temperature': value}
        except:
            return None
        finally:
            bus.release()


Working with MQTT
=================

The best way to work with MQTT is to use EVA ICS notification system
connections. Instead of creating own MQTT connection and manage topics, let EVA
core do its job. If your equipment and EVA ICS use different MQTT servers,
just create new MQTT notifier to equipment server in EVA ICS without any
subscriptions.

.. note::

    If **space** is specified in EVA MQTT notifier, all topics should be
    relative, e.g. if *space=test*, MQTT can send and subscribe only to topics
    below the space level: *equipment1/POWER* will send/subscribe to
    *test/equipment1/POWER*.

Use **eva.uc.drivers.tools.mqtt.MQTT** class to deal with notifiers. If no
notifier_id is specified **eva_1** notifier is used.

.. warning::

    MQTT custom handlers may be started in different threads. Don't forget to
    use locking mechanisms if required.

Let's deal with an equipment which has MQTT topic *topic/POWER* with values
*ON/OFF*:

.. code-block:: python

    # everything you need is just import class
    from eva.uc.drivers.tools.mqtt import MQTT
    # and a function to handle events
    from eva.uc.driverapi import handle_phi_event

    def __init__(self, phi_cfg=None, info_only=False):
    # ....
    self.topic = self.phi_cfg.get('t')
    self.mqtt = MQTT(self.phi_cfg.get('n'))
    self.current_status = { '1': None }
    if self.topic is None or self.mqtt is None:
        self.ready = False

    def get(self, port=None, cfg=None, timeout=0):
        # as we can not query equipment, return saved status instead
        return self.current_status


    def set(self, port=None, data=None, cfg=None, timeout=0):
        # .... check data, prepare
        try:
            state = int(data)
        except:
            return False
        # then use MQTT.send function to send data to desired topic
        self.mqtt.send(self.topic + '/POWER', 'ON' if state else 'OFF')
        return True

    def start(self):
        # register a custom handler for MQTT topic
        self.mqtt.register(self.topic + '/POWER', self.mqtt_handler)

    def stop(self):
        # don't forget to unregister a custom handler when PHI is unloaded
        self.mqtt.unregister(self.topic + '/POWER', self.mqtt_handler)

    def mqtt_state_handler(self, data, topic, qos, retain):
        # update current status
        self.current_status['1'] = 1 if data == 'ON' else 0
        # then handle PHI event
        handle_phi_event(self, 1, self.get())

Working with UDP API
====================

You may use EVA UDP API to receive custom UDP packets and then parse them in
PHI. This allows to create various hardware bridges e.g. from 315/433/866 MHz
radio protocols, obtaining radio packets with custom programmed hardware
appliance and then send them to EVA ICS to handle. 

Custom packet format is (\\x = hex):

    \\x01 HANDLER_ID \\x01 DATA

**DATA** is always transmitted to handler in binary format. UDP API encryption,
authentication and batch commands in custom packets are not supported (unless
managed by handler).

.. warning::

    UDP API custom handlers may be started in different threads. Don't forget to
    use locking mechanisms if required.

.. code-block:: python

    import eva.udpapi as udp

    def __init__(self, phi_cfg=None, info_only=False):
    # ....

    def start(self):
        # subscribe to UDP API using PHI ID as handler ID
        udp.subscribe(__id__, self.udp_handler)

    def stop(self):
        # don't forget to unsubscribe when PHI is unloaded
        udp.unsubscribe(__id__, self.udp_handler)

    def udp_handler(self, data, address):
        _data = data.decode()
        self.log_debug('got data: {} from {}'.format(_data, address))
        # process the data
        # ...

Exceptions
==========

The methods of PHI should not raise any exceptions and handle/log all errors by
themselves.

Testing
=======

Use **bin/test-phi** command-line tool to perform PHI module tests. The tool
requires test scenario file, which may contain the following functions:

* **debug()** turn on debug mode (verbose output), equal to *-D* command-line
  option

* **nodebug()** turn off debug mode

* **modbus(params)** create virtual ModBus port with ID *default*

* **load(phi_mod, phi_cfg=None)** load PHI module for tests. PHI cfg may be
  specified either as string or as dictionary

* **get(port=None, cfg=None, timeout=None)** call PHI **get** function

* **set(port=None, data=None, cfg=None, timeout=None)** call PHI **set**
  function

* **test(cmd=None)** call PHI **test** function

* **exec(cmd=None, args=None)** call PHI **exec** function

* **sleep(seconds)** delay execution for a given number of seconds (alias for
  *time.sleep*)

additionally, each function automatically prints the result. Test scenario is
actually a Python code and may contain any Python logic, additional module
imports etc.

Example test scenario. Let's test *dae_ro16_modbus* module:

.. code-block:: python

    debug()
    modbus('tcp:192.168.55.11:502')
    load('dae_ro16_modbus', 'port=default,unit=1')
    if test('self') != 'OK': exit(1)
    set(port=2,data=1)
    set(port=5,data=1)
    get()
    set(port=2,data=0)

