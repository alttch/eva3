Developing own PHI (Physical Interface) for EVA ICS. HOWTO
==========================================================

PHI (Physical interface) is low level driver which communicates directly with
an equipment. PHI should not contain any logic, it's job is only get/set
an equipment to state, requested by LPI.

Required variables in a header
------------------------------

PHI info
~~~~~~~~

* **__author__**        module author
* **__copyright__**     copyright
* **__license__**       module license
* **__version__**       module version
* **__description__**   module descrption (keep it short)

PHI system info
~~~~~~~~~~~~~~~

the next fields are processed by controller, so make them exactly as required

* **__id__**            module ID (usually equals to file name, string)
* **__equipment__**     supported equipment (list or string)
* **__api__**           module API (integer number)

* **__required__**      features required from LPI (Logical to Physical
  Interface, list):

 * **port_get** get single port data
 * **port_set** set single port data
 * **aao_get** get and process all ports at once
 * **aao_set** set all ports at once
 * **status** process item status
 * **value** process item values
 * **action** unit actions

* **__mods_required__**   required python modules (included neither in standard
  Python install nor in EVA ICS)

* **__features__**      own features provided (list):

 * **port_get** get single port data
 * **port_set** set single port data
 * **aao_get** get all ports at once (if no port specified)
 * **aao_set** set all ports at once (if list of ports and
   list of data is given)
 * **universal** PHI is universal and process **cfg** in requests.
 * **cache** PHI supports state caching (useful for a slow devices)

PHI help
~~~~~~~~

Each PHI module should contain 4 help variables:

* **__config__help__** module configuration help (on load)
* **__get_help__** additional configuration params which possible for LPI to
  send with **get** command
* **__set_help__** additional configuration params which possible for LPI to
  send with **set** command

First variable should be human readable, others may copy, join or process the
first one or each other in any way.

All variables should be in list format, containing dictionaries with the
following context:

* **name** property name
* **help** property description (help)
* **type** property type
* **required** *True* if proprery is required, *False* if it's optinal

Property **type** may be:

* **bool** boolean (True/False)
* **str** string
* **url** string containing url
* **int** integer
* **uint** unsigned integer (greater or equal to 0)
* **float** float number
* **ufloat** unsigned float (greater or equal to 0)
* **list:type** list of variables with type specified
* **enum:type:a,b,c** list of the permitted specified type values

The last one variable is

* **__help__**

It should contain the extended PHI description and operation manual. May be in
any variable format and use restructured text directives for the formatting.

Classes and modules
-------------------

It's allowed to import any Python system module or module installed by EVA ICS.
If PHI requires installing more modules, they should be listed in PHI readme
file.

.. warning::

    All non-standard modules (included neither in Python install nor in EVA
    ICS) should be imported with try/catch with **importlib**, their
    unavailability shouldn't block loading PHI for the informational puproses.

Importing modules from eva.uc.drivers.tools, eva.tools, eva.traphandler and
functions from eva.uc.driverapi:

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

    class PHI(GenericPHI):
        #<your code>

Constructor
-----------

The constructor should set the above constants to class variables to let them
be serialized by parent class if requested:

.. code-block:: python

    def __init__(self, phi_cfg=None, info_only=False):
        super().__init__(phi_cfg=phi_cfg, info_only=info_only)
        self.phi_mod_id = __id__
        self.__author = __author__
        self.__license = __license__
        self.__description = __description__
        self.__version = __version__
        self.__api_version = __api__
        self.__equipment = __equipment__
        self.__features = __features__
        self.__required = __required__
        self.__mods_required = __mods_required__
        self.__config_help = __config_help__
        self.__get_help = __get_help__
        self.__set_help = __set_help__
        self.__help = __help__
        if info_only: return
        # your code, i.e. to parse self.phi_cfg

The super().__init__ call should always be first.

If the constructor faces a problem (i.e. parsing a config or checking
equipment, i.e. local bus) it may set *self.ready=False* to abort controller
loading the driver.

If PHI methods get/set can't work with a single ports at all (i.e. equipment
returns state of all ports at once only), constructor should set variables:

* **self.aao_get=True** tells LPI the returned with PHI.get method data will
  always contain all port states
* **self.aao_set=True** asks LPI to collect as much data to set as possible, and
  then call PHI.set method

The parent constructor sets the variable **self.phi_cfg** to phi_cfg or to {},
so it's safe to work with it with *self.phi_cfg.get(cfgvar)*.

If **info_only** param is true, it means the controller loaded module only to
get its info and the module don't need to intialize itself for work and perform
initial tests.

Primary methods
---------------

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
    
    # if PHI can write data to the equipment
    def set(self, port=None, data=None, cfg=None, timeout=0):
        #<your code>
        #should return True (or result) if passed, False or None if failed

**port** and **data** may be integers, string, contain lists or be set as None.
PHI should always be ready to any incoming params and handle the missing or
incorrect by itself.

**cfg** may contain equipment configuration options. If the driver is
universal, it should handle them properly.

.. warning::

    watch out the timeout - if it's expired, the controller may crash or be
    forcely restarted.  Always calculate the remaining time for the external
    calls and return error as soon as it comes closer to the expiration.

This method should perform a self-test (equipment test) if cmd=='self', other
methods are variable and may be used i.e. for debugging. If command is not
understood by the method, it's a rule of a good taste to return a help text
(dict *{ 'command': 'command help' }*).

.. code-block:: python

    def test(self, cmd=None):
        #<your code>

The following methods may be used to call or register/unregister anything on
driver load/unload:

.. code-block:: python

    def start(self):
        #<your code>

    def stop(self):
        #<your code>


Parent methods
--------------

Parent class provides the following useful functions:

* **self.set_cached_state(data)** set driver cached state (any format)
* **self.get_cached_state()** return the state cached before. If the cache is
  expired (self.cache param handled by parent), the method return None

All the logging should be made with the following methods:

* **self.log_debug(msg)**
* **self.log_info(msg)**
* **self.log_warning(msg)**
* **self.log_error(msg)**
* **self.log_critical(msg)**
* **self.critical(msg)**

The last two methods do the same, logging an event and calling controller
critical() method.

Handling events
---------------

If the equipment sends some event, PHI should ask Driver API to handle it. This
can be done with method

.. code-block:: python

    eva.uc.driverapi.handle_phi_event(phi, port, data)

where:

* **phi** = **self**
* **port** = port, where the event has been happened
* **data** = port state values, as much as possible (dict *{'port': state }*)

The controller will call update() method for all items using the caller PHI for
updating, providing LPIs state data to let them process the event with
minimized amount of additional PHI.get() calls.

Value *-1* can be used to set unit error status, value *False* to set sensor
error status.

Handling SNMP traps
~~~~~~~~~~~~~~~~~~~

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
about the actual reaction time on a trap event) because every method is being
executed in the own thread.

EVA traphandler doesn't care about the method return value and you must process
all the errors by yourself.

Exceptions
----------

The methods of PHI should not raise any exceptions and handle/log all errors by
themselves.
