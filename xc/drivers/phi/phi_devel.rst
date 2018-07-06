Developing own PHI (Physical Interface) for EVA ICS. HOWTO
==========================================================

PHI (Physical interface) is low level driver which communicates directly with
an equipment. PHI should not contain any logic, it's job is only get/set
an equipment to state, requested by LPI.

Required fields in a header
---------------------------

* **__author__**        module author
* **__copyright__**     copyright
* **__license__**       module license
* **__version__**       module version
* **__description__**   module descrption (keep it short)

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

* **__features__**      own features provided (list):

 * **port_get** get single port data
 * **port_set** set single port data
 * **aao_get** get all ports at once (if no port specified)
 * **aao_set** set all ports at once (if list of ports and
   list of data is given)
 * **universal** the driver is universal and process **cfg** in requests.

* **__config_help__**   dict *{ 'prop_name': 'value' }*

Required parameters should be marked with * before the prop name (i.e. \*url).

Classes and modules
-------------------

It's allowed to import any Python system module or module installed by EVA ICS.
If PHI requires installing more modules, they should be listed in PHi readme
file.

Importing modules from eva.uc.drivers.tools, eva.tools and functions from
eva.uc.driverapi:

* **get_version()** get Driver API version
* **get_polldelay()** get EVA poll delay
* **get_timeout()** get default timeout
* **critical()** send EVA critical call
* **log_traceback()** log traceback debug info
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
be serialized by super() if requested:

.. code-block:: python

    def __init__(self, phi_cfg=None):
        super().__init__(phi_cfg=phi_cfg)
        self.phi_mod_id = __id__
        self.__author = __author__
        self.__license = __license__
        self.__description = __description__
        self.__version = __version__
        self.__api_version = __api__
        self.__equipment = __equipment__
        self.__features = __features__
        self.__required = __required__
        self.__config_help = __config_help__

The super().__init__ call should always be first.

If the constructor faces a problem (i.e. parsing a config) it may set
*self.ready=False* to abort controller loading the driver.

If PHI methods get/set can't work with a single ports at all (i.e. equipment
returns state of all ports at once only), constructor should set variables:

* **self.aao_get=True** tells LPI the returned with PHI.get method data will
  always contain all port states
* **self.aao_set=True** asks LPI to collect as much data to set as possible, and
  then call PHI.set method

Primary methods
---------------

The following methods should be defined. **cfg** param may contain
configuration params which should override the default ones for the current
call.

.. code-block:: python

    # if PHI can read data from the equipment
    get(self, port=None, cfg=None, timeout=0):
        #<your code>
        #should return a single state value or a dict { 'port': value }
        #should return None if failed
    
    # if PHI can write data to the equipment
    def set(self, port=None, data=None, cfg=None, timeout=0):
        #<your code>
        #should return True if passed, False if failed

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

