"""
EVA ICS plugin example

To load the plugin, put its config to the registry key,
config/<controller>/plugins/<plugin_name>

...........................................
enabled: true
config: {}
...........................................

Plugins can be one-file, in this case they can be just put into plugins
(/opt/eva/plugins) directory and named e.g. "my.py".

If your plugin is more complex or you want to redistribute it e.g. via PyPi -
create Python module called "evacontrib.<yourpluginname>" and install it either
globally or in EVA ICS venv.

Plugin configuration:

use either "eva <controller> edit plugin-config <plugin-name>" command or
edit the registry key eva3/HOST/config/<controller>/plugins/<plugin-name>

......
enabled: true
config:
  var1: value1
  var2: value2
......
"""

# plugin header, required
__author__ = 'Altertech, https://www.altertech.com/'
__copyright__ = 'Copyright (C) 2012-2021 Altertech'
__license__ = 'Apache License 2.0'
__version__ = "3.4.0"

# import EVA ICS Plugin API library
import eva.pluginapi as pa
"""
"flags" namespace can be defined, EVA ICS uses this namespace to determine
plugin status:

flags.ready = True # means plugin is correctly initialized and works properly
"""
from types import SimpleNamespace
flags = SimpleNamespace(ready=False)

# init plugin logger
logger = pa.get_logger()


def init(config, **kwargs):
    """
    Called by EVA ICS core when the initial configuration is loaded. All
    methods are optional, if the method doesn't exist in plugin, no exception
    is raised

    All methods should have **kwargs in argument list to accept extra arguments
    from future Plugin API versions

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
        # register SFA Templates function "weekend_days"
        pa.register_sfatpl_object('weekend_days', get_weekend)
    except:
        pass
    """
    register API extension blueprint

    currently only JSON RPC and direct API calling methods can be registered
    """
    pa.register_apix(MyAPIFuncs(), sys_api=False)
    flags.ready = True


def before_start(**kwargs):
    """
    Called right before controller start
    """
    logger.info('plugin my before start called')


def start(**kwargs):
    """
    Called after controller start
    """
    logger.info('plugin my start called')


def before_stop(**kwargs):
    """
    Called right before controller stop
    """
    logger.info('plugin my before stop called')


def stop(**kwargs):
    """
    Called after controller stop
    """
    logger.info('plugin my stop called')


def dump(**kwargs):
    """
    Called after controller stop
    """
    return 'something'


def handle_state_event(source, data, **kwargs):
    """
    Called when any state event is received

    Args:
        source: event source item (object)
        data: serialized item state dict
    """
    logger.info(f'event from {source.oid}')
    logger.info(data)


def handle_api_call(method, params, **kwargs):
    """
    Called before API methods

    If returned False, API raises FunctionFailed exception
    If any standard PluginAPI exception is raised, API returns the correspoding
    error

    Args:
        method: method name
        params: method params
    """
    logger.info(f'API METHOD CALLED: {method} with params {params}')
    if method == 'destroy':
        raise pa.AccessDenied('Method is disabled')


def handle_api_call_result(method, params, result, **kwargs):
    """
    Called after API methods

    If returned False, API raises FunctionFailed exception
    If any standard PluginAPI exception is raised, API returns the correspoding
    error

    Args:
        method: method name
        params: method params
        result: method result
    """
    logger.info(f'API METHOD: {method} with params {params}, RESULT: {result}')


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
        # if API method produces no result, it SHOULD return True
        return {
            'result': x * x,
            'you': pa.get_aci('key_id'),
            'me': [pa.get_directory('eva'),
                   pa.get_product().build]
        }

    # log API call as INFO
    @pa.api_log_i
    # require master key
    @pa.api_need_master
    def my_test(self, **kwargs):
        # let's return the result of test_phi API function
        return pa.api_call('test_phi', i='ct1', c='self')
