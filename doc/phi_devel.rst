Developing own PHI (Physical Interface) for EVA ICS. HOWTO
**********************************************************

PHI (Physical interface) is a low level driver which communicates directly with
an equipment. PHI should not contain any logic, its job is only to get/set an
equipment to the state requested by LPI.

.. contents::

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
* **__api__**           module API (integer number), current is **10**

* **__required__**      features required from LPI (Logical to Physical
  Interface, list):

 * **aao_get** get and process all ports at once (bulk)
 * **aao_set** set all ports at once (bulk)
 * **action** unit actions
 * **events** event processing
 * **port_get** get single port data
 * **port_set** set single port data
 * **push** accept state payload via *push_phi_state* API method
 * **status** process item status
 * **value** process item values

* **__mods_required__** required python modules (not included neither in
  standard Python install nor in EVA ICS)

* **__lpi_default__** if specified, the default driver will be created for this
  PHI when loaded.

* **__features__**      own features provided (list, features from __required__
  are automatically included):

 * **aao_get** PHI can return state of all ports at once but can work with a
   single ports as well
 * **aao_set** PHI can set state of all ports at once but can work with a
   single ports as well
 * **universal** PHI is universal and process **cfg** in requests.
 * **cache** PHI supports state caching (useful for slow devices)

* **__discover__** string or list, which describes how "discover" method (if
  implemented) will search for the equipment: **net** for network or EVA ICS
  bus name (*modbus*, *owfs* etc.)

* **__shared_namespaces__** list of shared namespaces used by PHI. If you are
  going to use shared namespaces, listing them in this variable is
  **required**, otherwise PHI will have no access to them.

PHI help
--------

Each PHI module should contain 4 help variables:

* **__config__help__** module configuration help (on load)
* **__get_help__** additional configuration params possible for LPI to send
  with **get** command
* **__set_help__** additional configuration params possible for LPI to send
  with **set** command
* **__discover_help__** help for "discover" method

First variable should be human readable, others may copy, join or process the
first one or each other in any way.

All variables should be in list format, containing dictionaries with the
following context:

* **name** property name
* **help** property description (help)
* **type** property type
* **required** *True* if property is required, *False* if it's optional
* **default** default value (for required only)

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
* **any** any type
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
* **get_system_name()** get system name
* **critical()** send EVA critical call
* **log_traceback()** log traceback debug info
* **lock(l, timeout, expires)** acquire lock "eva:phi:**l**", wait max
  **timeout** sec, lock automatically expires in **expires** sec. Timeout and
  expiration time can't be longer than default controller timeout.
* **unlock(l)** release lock "eva:phi:**l**"
* **handle_phi_event(phi, port, data)** ask Driver API to handle event (see
  below)

is highly welcome. Importing other EVA modules or Driver API functions is not
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
        #should return a single state value or a dict { 'port': value } (for
        # bulk or ssp/usp), port should always be a string
        #
        #should return None if failed, integer for status, string for values
        #
        #if PHI supports aao_get feature, it should return all port states when
        #no port is specified in request.
        #
        # for unit status, "value" should be integer. if unit PHI has "value"
        # feature, it should return either (status, value) tuple or a dict
        # {'port':(status,value}
    
    # if PHI can write data to the equipment
    def set(self, port=None, data=None, cfg=None, timeout=0):
        #<your code>
        #should return True (or result) if passed, False or None if failed
        #
        #If PHI supports aao_set feature, it should deal with a list of ports,
        #if no - with a single port only. If both port_set and aao_set are
        #specified in features, PHI should deal with both single port and list
        #of ports
        #
        #on bulk requests, both port and data are lists
        #
        #if unit PHI has "value" feature, the data contains either single or
        #multiple (status, value) tuples

.. note::

    If unit action is called without value, PHI **set** method is called with
    previous known unit value

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

    def unload(self):
        # called when PHI is unloaded from the controller
        #<your code>


Parent methods
==============

Parent class provides the following useful functions:

* **self.set_cached_state(data)** set driver cached state (any format)
* **self.get_cached_state()** return the state cached before. If the cache is
  expired (self.cache param handled by parent), the method return None

.. warning::

    If *get_cached_state()* method is used, PHI should return a **copy** of
    cached object

All the logging should be done with the following methods:

* **self.log_debug(msg)**
* **self.log_info(msg)**
* **self.log_warning(msg)**
* **self.log_error(msg)**
* **self.log_critical(msg)**
* **self.critical(msg)**

The last two methods do the same, logging an event and calling controller
critical() method.

* **self.get_shared_namespace(namespace_id)** returns namespace object,
  shared between all PHIs.

Optional methods
================

get_phi_ports
-------------

The method should be implemented if you want to let PHI to respond to API
"get_phi_ports" method.

.. code-block:: python

    def get_ports(self):
        #<your code>

The method should return list of dictionaries with "port", "name" and
"description" fields. Are fields are required and should be strings.

If hardware equipment always has fixed amount of ports and they all are used
for the same purpose (e.g. relay), you may use parent function
*generate_port_list*:

.. code-block:: python

        def get_ports(self):
            return self.generate_port_list(
                port_max=16, description='relay port #{}')

        # parent function has the following params:
        # def generate_port_list(
        #       port_min=1, port_max=1, name='port #{}', description='port #{}')

discover
--------

The method should be implemented if you want let PHI to respond to API
"phi_discover" method and should return all supported equipment discovered,
including parameters for PHI loading.

"discover" method should be always implemented as static as it is always called
on module, before PHI is loaded and primary class is created. If PHI implements
discovery, *__discover__* header should always be present in module.

.. code-block:: python

    __discover__ = 'net'

    # ............

        @staticmethod
        def discover(interface=None, timeout=0):
            # interface - network or bus name, can be list or string
            #<your code>

The method should return array of dictionaries, which may contain any fields.
Field *!load* is required and should contain dictionary with PHI loading
params, e.g. *{ 'host': '<ip_of_hardware>' }*.

You may specify result column ordering for EVA ICS interfaces. For that, a
special record:

.. code-block:: python

    [{ '!opt': 'cols', 'value': [<columns>]}]

must be present as first in a result. A special column *'!load'* in a
column list is not required.

Config validation
=================

Optional method *validate_config* can be implemented to automatically validate
module configuration.

.. include:: pydoc/pydoc_validateconfig.rst

Working with unit values
========================

For units, method **get** can return either single integer (*status*) or a
state tuple (*status*, *value*). If *value* is set to *None*, it is ignored
and only status is updated. LPI automatically detects output data and parses
either status or (status, value) pair.

For method **set**, by default data contains either *status* (integer) or a
list of integers only. To accept extended state (*status, value* tuple or a
list of tuples) for **set**, **value** string must be specified in
**__required__** header list variable.

Handling timeouts
=================

Starting from DriverAPI v8, timeout handling can be easily performed with
**timeouter** library (https://github.com/alttch/timeouter). The library is
included into EVA ICS by default and can be imported by any PHI module.

When PHI is executed, timeouter library is already initialized for the running
thread, and you may use its methods:

.. code-block:: python

   import timeouter as to
   from eva.uc.driverapi import log_traceback

   # .........

      def get(self, port=None, cfg=None, timeout=0):
         # Some call requires 3 seconds, abort if we will be out of time
         if not to.has(3): return None
         # does the same
         if to.get() < 3: return None
         try:
            # .... perform some calls
            # calculate timeout for external call:
            # e.g. you must specify timeout for some function, which will
            # perform 3 retries (4 total attempts) to get data from the
            # equipment:
            somefunc(retries=3, timeout=to.get(laps=4))

            # raises eva.exceptions.TimeoutException
            # if timeout has expired
            to.check()
         except:
            log_traceback()
            return None

Parameter **timeout** for *get*/*set* functions is filled for the backward
compatibility.

.. note::

   Allowed timeout is always slightly lower than specified in
   *action_timeout*/*update_timeout*, as some part of time is used to execute
   driver LPI code.

Handling events
===============

Incoming events
---------------

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

State push
----------

External applications can push state directly to PHI module. The module should
handle state push by itself, calling *handle_phi_event* for each modified port
if required.

Application calls *push_phi_state* method (see UC API doc), providing state
payload, which should be parsed and processed by PHI module. The following
method should be implemented:

.. code-block:: python

    class PHI(GenericPHI):

        # class code

      def push_state(self, payload):
         # process payload, return True if OK, False if failed
         return True

The method receives external state payload as-is. State payload can be in any
format, acceptable by PHI.

SNMP traps
----------

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

Schedule updates
----------------

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

    @phi_constructor
    def __init__(self, **kwargs):
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


Working with Modbus
===================

Working with Modbus is pretty easy. PHIs don't need to care about the Modbus
connection and data exchange at all, everything is managed by
**eva.uc.drivers.tools.modbus** module. The module provides methods for reading
all popular data types (booleans, 16-, 32- and 64-bit signed/unsigned integers
and IEEE 754 floats).

.. note::

    Direct import of eva.uc.modbus is deprecated since EVA ICS 3.3.2 (DriverAPI
    v10)

.. code-block:: python

    # everything you need is just import module
    import eva.uc.drivers.tools.modbus as modbus
    from eva.uc.driverapi import log_traceback

    @phi_constructor
    def __init__(self, **kwargs):
        # ....
        # it's recommended to force aao_get in Modbus PHI to let it read states
        # with one modbus request
        self.modbus_port_id = self.phi_cfg.get('port')
        # check in constructor if the specified modbus port is defined
        if not modbus.is_port(self.modbus_port_id):
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
        try:
            modbus_port = modbus.get_port(self.modbus_port_id, timeout)
        except Exception as e:
            self.log_error(e)
            log_traceback()
            return None
        # The port object is a regular pymodbus object
        # (https://pymodbus.readthedocs.io) and supports all pymodbus functions.
        # All the functions are wrapped with EVA modbus module which handles
        # all errors and retry attempts. The ports PHI gets are always in the
        # connected state. The port methods can be used for bulk or complicated
        # requests

        # For single values of standard data types, modbus tool module is
        # recommended

        # read 16 coils, starting from 0
        try:
            coils = modbus.read_bool(modbus_port, 'c0', 16, unit=self.unit_id)
        except:
            return None
        finally:
            # Release modbus port as soon as possible to let other components
            # work with it while your PHI is processing the data
            modbus_port.release()

        # let's convert 16 booleans to 16 port states
        result = {}
        try:
            for i in range(16):
                result[str(i + 1)] = 1 if coils[i] else 0
        except:
            result = None
        return result


The variable **client_type** of the port object (*modbus_port.client_type*)
holds the port type (tcp, udp, rtu, ascii or binary). This can be used to make
PHI work with the equipment of the same type which uses e.g. different
registers for different connection types.


Working with Ethernet/IP
========================

The standard way to work with Ethernet/IP devices in EVA ICS is `cpppo
<https://github.com/pjkundert/cpppo/>`_ Python module. The module isn't
installed by default. Append *cpppo* to "extra:" section of *config/venv* EVA
registry key and rebuild EVA ICS venv (*eva feature setup venv*).

Here is helper usage example:

.. code-block:: python

    # ........
    from eva.uc.driverapi import log_traceback

    class PHI(GenericPHI):

        def get(self, port=None, cfg=None, timeout=0):
            # do not import anything in the main module code as cpppo module
            # isn't included by default
            from eva.uc.drivers.tools.cpppo_enip import operate
            try:
                result, failures = operate(
                    host=self.phi_cfg['host'],
                    port=self.phi_cfg['port'],
                    tags=[port])
                if failures:
                    raise RuntimeError
                else:
                    # the module example returns unit status (int)
                    return int(result[0][0])
            except:
                log_traceback()
                return None

        def set(self, port=None, data=None, cfg=None, timeout=0):
            from eva.uc.drivers.tools.cpppo_enip import operate
            try:
                _, failures = operate(
                    host=self.phi_cfg['host'],
                    port=self.phi_cfg['port'],
                    tags=[f'{port}={data}'])
                if failures:
                    raise RuntimeError
                else:
                    return True
            except:
                log_traceback()
                return False

The helper function arguments are similar to *cpppo.server.enip.client* command
line arguments. Refer to function pydoc or CLI help for more details.

The above method is simple but it isn't recommended for the high load
environments, as "operate" functions creates new connector for each request. To
reuse connections, it's recommended to use **SafeProxy** class. Refer to
*eva.uc.drivers.tools.cpppo_enip pydoc* for more info.


Working with Modbus slave memory space
======================================

Universal Controller can perform basic data processing as Modbus slave, custom
PHI can do this more flexible. E.g. there's temperature sensor, which reports
its value multiplied by 100. As Modbus registers don't support floats, custom
PHI module can listen to the register and automatically divide value by 100
before sending update to UC item.

Multiple items and PHIs can watch the same register and perform data processing
independently.

.. code-block:: python

    import eva.uc.modbus as modbus

    @phi_constructor
    def __init__(self, **kwargs):
    # ....

    def start(self):
        # watch changes of Modbus slave register
        # addr - value from 0 to 9999
        # self.process_modbus - function to process Modbus data
        # register - 'h' for holding (default), 'i' for input,
        #            'c' for coil and 'd' for discrete input
        modbus.register_handler(addr, self.process_modbus, register='h')

    def stop(self):
        # don't forget to unregister handler when PHI is unloaded
        modbus.unregister_handler(addr, self.process_modbus, register='h')

    def process_modbus(self, addr, values):
        # the function is called as soon as watched Modbus register is changed
        # parameters: addr - memory address, values - values written (list)
        #
        # values of holding and input registers are arrays of 2-byte integers
        # values of coils and discrete inputs - arrays of booleans (True/False)
        #
        # as input registers and discrete inputs are read-only for external
        # devices, they can be changed only by another local PHI module or UC
        # itself
        #
        _data = values[0]
        self.log_debug('got data: {} from {}'.format(_data, addr))
        # process the data
        # ...

PHI can also manipulate data in Modbus slave memory blocks manually, to do this
use functions:

.. code-block:: python

    get_data(addr, register='h', count=1)
    # and
    set_data(addr, values, register='h')
    # ("values" should be a list (of unsigned integers or booleans, depending
    # on memory block type)


Working with 1-Wire via OWFS
============================

As EVA ICS has virtual OWFS buses, you don't need to initialize OWFS by
yourself. Import **eva.uc.drivers.tools.owfs** module to get an access to all
defined virtual OWFS buses.

Methods available:

* **owfs.is_bus(bus_id)** returns *True* if bus is defined
* **bus = owfs.get_bus(bus_id)** get bus. If locking is defined, the bus becomes
  exclusively locked.
* **bus.read(path, attr)** read equipment attribute value
* **bus.write(path, attr, value)** write equipment attribute value
* **bus.release()** Release bus. As bus may be locked for others, the method
  should be always called immediately after the work with bus is finished.

.. note::

    Direct import of eva.uc.owfs is deprecated since EVA ICS 3.3.2 (DriverAPI
    v10)

.. code-block:: python

    # everything you need is just import module
    import eva.uc.drivers.tools.owfs as owfs
    from eva.uc.driverapi import log_traceback

    @phi_constructor
    def __init__(self, **kwargs):
        # ....
        # it's recommended to force aao_get in Modbus PHI (list it in
        # __required__) to let it read states # with one modbus request
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
        try:
            bus = owfs.get_bus(self.owfs_bus)
        except Exceptions as e:
            self.log_error(e)
            log_traceback()
            return None
        try:
            value = bus.read(path, 'temperature')
            if not value:
                raise Exception('can not obtain temperature value')
            return {'temperature': value}
        except:
            return None
        finally:
            bus.release()


Working with SNMP
=================

Performing get/set calls
------------------------

EVA ICS has bindings to primary `pysnmp <https://pypi.org/project/pysnmp/>`_
methods, which can be found in *eva.uc.drivers.tools.snmp* module. Pysnmp is a
reach-feature SNMP module and is included in setup by default, however this
module is not recommended to use on a slow hardware in production.

The rule of good taste is to check if alternative (faster) SNMP module is
present (such as e.g. `python3-netsnmp
<https://pypi.org/project/python3-netsnmp/>`_) and use it for a regular get/set
functions instead:

.. code-block:: python

    import eva.uc.drivers.tools.snmp as snmp
    try:
        import netsnmp
    except:
        netsnmp = None

    #....................................
    #....................................
    #....................................

    if netsnmp:
        # ... use netsnmp module
    else:
        # ... use default pysnmp module

.. note::

    It is always better to perform a single getbulk request rather than using
    get/walk SNMP methods.

SNMP MIBs
---------

As PHI is always written for the specific known equipment, there's usually no
need to use SNMP MIBs and dotted number SNMP OIDs are used instead.

If you plan to use SNMP MIBs, you should warn user to download them and place
to the proper location or include MIB directly into PHI code to generate it on
the flow.


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

    @phi_constructor
    def __init__(self, **kwargs):
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

    @phi_constructor
    def __init__(self, **kwargs):
    # ....

    def start(self):
        # subscribe to UDP API using PHI ID as handler ID
        udp.subscribe(__name__, self.udp_handler)

    def stop(self):
        # don't forget to unsubscribe when PHI is unloaded
        udp.unsubscribe(__name__, self.udp_handler)

    def udp_handler(self, data, address):
        _data = data.decode()
        self.log_debug('got data: {} from {}'.format(_data, address))
        # process the data
        # ...

Discovering SSDP hardware
=========================

If "discover" method is implemented and discovers hardware equipment via SSDP,
driver tool can be used:

.. code-block:: python

    def discover(interface=None, timeout=0):
        import eva.uc.drivers.tools.ssdp as ssdp
        result = ssdp.discover(
            'upnp:all',
            interface=interface,
            timeout=timeout,
            discard_headers=[
                'Cache-control', 'Ext', 'Location', 'Host'
            ])
        # if upnp:all is used - filter result to leave only supported hardware

    # eva.uc.drivers.tools.ssdp.discover function has the following params:
    # def discover(st,
    #             ip='239.255.255.250',
    #             port=1900,
    #             mx=True,
    #             interface=None,
    #             trailing_crlf=True,
    #             parse_data=True,
    #             discard_headers=['Cache-control', 'Host'],
    #             timeout=None)
    # where
    #   mx                  send MX header or not
    #   trailing_crlf       append trailing CR/LF at the end of request
    #   parse_data          try parsing data automatically
    #   discard_headers     discard specified headers if data is parsed


Shared namespaces
=================

Some equipment modules or system libraries don't allow to retake ownership on
the particular device once it's initialized until the process restart. As the
result, *phi reload* and *phi set* (*set* command reloads PHI module with the
new params) methods for such devices will not work.

There are tons of libraries and buses and we can not integrate everything in
EVA ICS to provide native functions. For that, we offer you to use shared
namespaces.

Shared namespace is a simple object, shared between all PHIs in system.
Namespace ids you plan to use should be always listed in
**__shared_namespaces__** module header.

After, you can obtain shared namespace at any time, by calling
*self.get_shared_namespace(namespace_id)*.

Namespace object methods:

* **has(obj_id)** returns *True* if namespace has specified object
* **set(obj_id, val)** set namespace object to the specified value *
  **get(obj_id, default=None)** get namespace object, set it to *default* value
  if doesn't exist.
* **locker** *threading.RLock()* object which can be used to safely manipulate
  objects inside namespace.

.. warning::

    Don't manipulate thread-unsafe objects inside namespace without
    thread-locking.

Example:

.. code-block:: python

    __shared_namespaces__ = ['gpiozero']

    # ......

    ns = self.get_shared_namespace('gpiozero')
    with ns.locker:
        d_id = 'port_'.format(port)
        if ns.has(d_id):
            gpio_device = ns.get(d_id)
        else:
            gpio_device = gpiozero.DigitalOutputDevice(port)
            ns.set(d_id, gpio_device)


Asynchronous I/O
================

Calls to PHIs are always synchronous. If equipment can set multiple ports at
once or PHI can provide asynchronous features itself, it should have
*aao_get*/*aao_set* in *__features__* or *__required__* lists.

The difference between last two is that *__required__* **requires** parent LPI
to have a feature for working with multiple ports at once and PHI get/set
methods always get list of ports/data.

While *__features__* **allows** LPI to send multi-port command, however it can
be single as well. In this case get/set methods of PHI should manually check
incoming data format (single value or list).

You, as PHI developer, always choose by yourself the way how to work with
multiple hardware ports at once: get/set multiple registers or special "group"
registers (e.g.  for Modbus or SNMP), use asynchronous HTTP API calls or launch
multiple threads. However, using *aao_get*/*aao_set* is always good practice
and recommended if possible.


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

* **modbus(params)** create virtual Modbus port with ID *default*

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

