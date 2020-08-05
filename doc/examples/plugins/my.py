"""
EVA ICS plugin example

To load the plugin, put its name to controller config, section [server]

e.g. edit etc/uc.ini:

...........................................
[server]
plugins = my ; plugin list, comma separated
...........................................

Plugins can be one-file, in this case they can be just put into plugins
(/opt/eva/plugins) directory and named e.g. "my.py".

If your plugin is more complex or you want to redistribute it e.g. via PyPi -
create Python module called "evacontrib.<yourpluginname>" and install it either
globally or in EVA ICS venv.

Plugin configuration

Put a section [<pluginname>] in controller config, e.g. for this plugin:

......
[my]
var1 = value1
var2 = value2
......
"""

# plugin header, required
__author__ = "Altertech, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2020 Altertech"
__license__ = "Apache License 2.0"
__version__ = "0.0.1"

# import EVA ICS Plugin API library
import eva.pluginapi as pa
"""
"flags" namespace can be defined, EVA ICS uses this namespace to determine
plugin status:

flags.ready = True # means plugin is correctly initialized and works properly
"""
from types import SimpleNamespace
flags = SimpleNamespace(ready=False)

import logging

# create plugin logger
logger = logging.getLogger('eva.plugin.my')


def init(config):
    """
    Called by EVA ICS core when the initial configuration is loaded. All
    methods are optional, if the method doesn't exist in plugin, no exception
    is raised

    Args:
        config: plugin configuration (comes as key/value dict)
    """
    # require Plugin API version 1+
    pa.check_version(1)
    # this feature is only for LM PLC
    try:
        pa.check_product('lm')
        # register new lmacro function "mytest"
        pa.register_lmacro_object('mytest', mytest)
        # register lmacro object "weekend"
        pa.register_lmacro_object('weekend', weekend)
    except:
        pass
    # this feature is only for SFA
    try:
        pa.check_product('sfa')
        # register SFA Templates function "get_weekend"
        pa.register_sfatpl_object('weekend_days', get_weekend)
    except:
        pass
    """
    register API extension blueprint

    currently only JSON RPC and direct API calling methods can be registered
    """
    pa.register_apix(MyAPIFuncs(), sys_api=False)
    flags.ready = True


def before_start():
    """
    Called right before controller start
    """
    logger.info('plugin my before start called')


def start():
    """
    Called after controller start
    """
    logger.info('plugin my start called')


def before_stop():
    """
    Called right before controller stop
    """
    logger.info('plugin my before stop called')


def stop():
    """
    Called after controller stop
    """
    logger.info('plugin my stop called')


def dump():
    """
    Called after controller stop
    """
    return 'something'


def handle_state_event(source, data):
    """
    Called when any state event is received

    Args:
        source: event source item (object)
        data: serialized item state dict
    """
    logger.info('event from', source.oid)
    logger.info(data)


# custom plugin code

weekend = ['Sat', 'Sun']


# the function we registered for SFA TPL
def get_weekend():
    return ','.join(weekend)


# the function we registered for LM PLC macros
def mytest():
    logger.info('something')


# APIX blueprint to implement new API functions
class MyAPIFuncs(pa.APIX):

    # log API call as DEBUG
    @pa.api_log_d
    # require master key
    @pa.api_need_master
    def my_square(self, **kwargs):
        # parse incoming params
        x = pa.parse_api_params(kwargs, 'x', 'N')
        if x < 0:
            raise pa.InvalidParameter('x < 0')
        # return some result
        return {'result': x * x, 'you': pa.get_aci('key_id')}

    # log API call as INFO
    @pa.api_log_i
    # require master key
    @pa.api_need_master
    def my_test(self, **kwargs):
        # let's return the result of test_phi API function
        return pa.api_call('test_phi', i='ct1', c='self')
