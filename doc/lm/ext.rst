Macro extensions
****************

As macros are written in Python, you can use any Python module to extend your
macros. Additionally :doc:`/lm/lm` has ability to extend macros with
extensions.

Modules are more flexible and are a standard Python way to extend your software.
However macro extensions are more simple, standardized and easy to configure.
As the goal is to keep macro code as simple as possible, macro extensions are
the best choice in many cases.

.. contents::

Loading macro extension
=======================

Macro extensions are stored in *xc/extensions* folder. To list available macro
extension modules, use command:

.. code-block:: bash

    eva lm ext mods

Next command returns extension info:

.. code-block:: bash

    eva lm ext modinfo <ext_module>

To get information about extension configuration and functions provided, use
commands:

.. code-block:: bash

    eva lm ext modhelp <ext_module> cfg
    eva lm ext modhelp <ext_module> functions

To load/unload macro extension, use command:

.. code-block:: bash

    # load
    eva lm ext load [-c CONFIG] [-y] <ext_id> <ext_module>
    # unload
    eva lm ext unload <ext_id>

where:

* **-c CONFIG** extension configuration options, comma separated
* **-y** save extension config after successful load

Extension functions
===================

When extension is loaded, its functions become available in all
:doc:`macros</lm/macros>` automatically with names *<ext_id>_<function>*.

E.g. when extension **audio** is loaded with ID **a1**, its function **play**
is available as **a1_play**. This allows you to load one extension multiple
times and have different functionality according to specified configuration
without need to configure module/class params in macros.

If you want to make a short alias for extension function, use
:ref:`alias<macro_api_alias>` (e.g. in *xc/lm/common.py*):

.. code-block:: python

    alias('play', 'a1_play')

Unlike *play=a1_play* **alias** doesn't throw an exception and let macros work
even if extension is failed to load or its functions are not available.

Included extensions
===================

The following extensions are included in EVA ICS distribution by default:

* **audio** plays audio files

* **rpush** notifications via Roboger (https://www.roboger.com/,
  https://github.com/alttch/roboger)

* **run_remote** execute macro on any remote :doc:`/lm/lm`

* **tts** Text-to-speech engine via Altertech TTS Broker
  (https://pypi.org/project/ttsbroker/)

Developing your own extension
=============================

Create new Python file in *xc/extensions* folder.

Required variables in a header
------------------------------

* **__author__**        module author
* **__copyright__**     copyright
* **__license__**       module license
* **__version__**       module version
* **__description__**   module description (keep it short)
* **__api__**           module API (integer number), current is **7**
* **__mods_required__** required python modules (included neither in standard
  Python install nor in EVA ICS)
* **__config__help__**  module configuration help (on load)
* **__functions__**     exported functions
* **__help__** should contain the extended description and operation manual.
  May be in any variable format and use restructured text directives for
  formatting.

Configuration variable
----------------------

Configuration variable (**__config_help__**) should be in list format,
containing dictionaries with the following context:

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
* **enum:type:a,b,c** list of permitted specified type values

If a property accepts multiple types, they should be listed via *or* (**|**)
symbol.

Exported functions
------------------

Exported functions (**__functions__**) variable is a dictionary in format:

.. code-block:: python

    { 'function(params)': 'description' }
    # e.g.
    {
        'func1(param1, param2=0, param3=True)': 'This function does something',
        'func2(param1=0)': 'This function does something else'
    }

All exported functions should be defined in a primary extension class.

Classes and modules
-------------------

It's allowed to import any Python system module or module installed by EVA ICS.
If extension requires installing more modules, they should be listed in
extension help and in **__mods_required__** variable.

.. warning::

    All non-standard modules (not included neither in Python install nor in EVA
    ICS) should be imported with try/catch with **importlib**, their
    unavailability shouldn't block loading extension for informational
    purposes.

Importing EVA modules and functions from **eva.lm.extapi**:

* **get_version()** get Extension API version
* **get_polldelay()** get EVA poll delay
* **get_timeout()** get default timeout
* **critical()** send EVA critical call
* **log_traceback()** log traceback debug info
 
is highly welcome.

The main class is defined as:

.. code-block:: python

    from eva.lm.extensions.generic import LMExt as GenericExt
    from eva.lm.extapi import ext_constructor
    
    class LMExt(GenericExt):
        #<your code>

Constructor
-----------

The constructor should set the above constants to class variables to let them
be serialized by parent class if requested:

.. code-block:: python

    @ext_constructor
    def __init__(self, **kwargs):
        # your code, e.g. parsing self.cfg

Decorator *@ext_constructor* automatically invokes parent constructor and
handles special init requests.

If the constructor faces a problem (i.e. parsing a config or checking
required modules) it may set *self.ready=False* to abort controller loading the
extension.

Persistent data
---------------

Special dict variable **self.data** is used to keep extension persistent data.
This data is automatically saved on controller stop or when **save** API
/ CLI command is called and automatically loaded on controller start.

Requirements:

* **self.data** should always be a dict

* dict keys, as well as keys of the sub-dicts must be strings

* data is stored in JSON format, so should contain only numbers, strings and
  booleans, lists and dicts

* it's highly recommended to use *self.data_lock* before accessing *self.data*

* to tell controller that data is modified and should be saved, set
  *self.data_modified* to *True*

Code example:

.. code-block:: python

   # read data
   with self.data_lock:
      value = data.get('key')

   # write data
   with self.data_lock:
      data['key'] = 'value'
      self.data_modified = True

.. warning::

   When extesion is unloaded, its data file is deleted

Exceptions
----------

There's no standard way to handle exceptions, however if any of exported
functions raise them, this should be specified in extension help and readme
file.

Config validation
-----------------

Optional method *validate_config* can be implemented to automatically validate
module configuration.

.. include:: ../pydoc/pydoc_validateconfig.rst

Testing
-------

Use **bin/test-ext** command-line tool to perform PHI module tests. The tool
requires test Python file, which loads extension as *_* and contains all its
functions (e.g. *__test* for *extension.test*):

.. code-block:: python

    print('Testing extension')
    __test(params)
    __func2(params)
    __func3(params)
    print('Test completed')

