
.. py:module:: eva.pluginapi


.. py:class:: APIX()
   :module: eva.pluginapi

   API blueprint extension class
   

.. py:exception:: AccessDenied(msg='', kb=None)
   :module: eva.pluginapi

   raised when call has no access to the resource
   
   
   .. py:method:: AccessDenied.__str__()
      :module: eva.pluginapi
   
      Return str(self).
      

.. py:exception:: FunctionFailed(msg='', kb=None)
   :module: eva.pluginapi

   raised with function failed with any reason
   
   
   .. py:method:: FunctionFailed.__str__()
      :module: eva.pluginapi
   
      Return str(self).
      

.. py:exception:: InvalidParameter
   :module: eva.pluginapi

   
   .. py:method:: InvalidParameter.__str__()
      :module: eva.pluginapi
   
      Return str(self).
      
   
   .. py:attribute:: InvalidParameter.__weakref__
      :module: eva.pluginapi
   
      list of weak references to the object (if defined)

.. py:class:: MQTT(notifier_id)
   :module: eva.pluginapi

   MQTT helper class
   
   :param notifier_id: MQTT notifier to use (default: eva_1)
   
   
   .. py:method:: MQTT.__init__(notifier_id)
      :module: eva.pluginapi
   
      :param notifier_id: MQTT notifier to use (default: eva_1)
      
   
   .. py:attribute:: MQTT.__weakref__
      :module: eva.pluginapi
   
      list of weak references to the object (if defined)
   
   .. py:method:: MQTT.register(topic, func, qos=1)
      :module: eva.pluginapi
   
      Register MQTT topic handler
      
   
   .. py:method:: MQTT.send(topic, data, retain=None, qos=1)
      :module: eva.pluginapi
   
      Send MQTT message
      
   
   .. py:method:: MQTT.unregister(topic, func)
      :module: eva.pluginapi
   
      Unregister MQTT topic handler
      

.. py:exception:: MethodNotFound
   :module: eva.pluginapi

   raised when requested method is not found
   
   
   .. py:method:: MethodNotFound.__str__()
      :module: eva.pluginapi
   
      Return str(self).
      
   
   .. py:attribute:: MethodNotFound.__weakref__
      :module: eva.pluginapi
   
      list of weak references to the object (if defined)

.. py:exception:: MethodNotImplemented(msg='', kb=None)
   :module: eva.pluginapi

   raised when requested method exists but requested functionality is not
   implemented
   
   
   .. py:method:: MethodNotImplemented.__str__()
      :module: eva.pluginapi
   
      Return str(self).
      

.. py:exception:: ResourceAlreadyExists(msg='', kb=None)
   :module: eva.pluginapi

   raised when requested resource already exists
   
   
   .. py:method:: ResourceAlreadyExists.__str__()
      :module: eva.pluginapi
   
      Return str(self).
      

.. py:exception:: ResourceBusy(msg='', kb=None)
   :module: eva.pluginapi

   raised when requested resource is busy (e.g. can't be changed)
   
   
   .. py:method:: ResourceBusy.__str__()
      :module: eva.pluginapi
   
      Return str(self).
      

.. py:exception:: ResourceNotFound(msg='', kb=None)
   :module: eva.pluginapi

   raised when requested resource is not found
   
   
   .. py:method:: ResourceNotFound.__str__()
      :module: eva.pluginapi
   
      Return str(self).
      

.. py:exception:: TimeoutException(msg='', kb=None)
   :module: eva.pluginapi

   raised when call is timed out
   

.. py:function:: api_call(method, key_id=None, **kwargs)
   :module: eva.pluginapi

   Call controller API method
   
   :param key_id: API key ID. If key_id is None, masterkey is used
   :param other: passed to API method as-is
   
   :returns: API function result
   
   :raises eva.exceptions:
   

.. py:function:: api_log_d(f)
   :module: eva.pluginapi

   API method decorator to log API call as DEBUG
   

.. py:function:: api_log_i(f)
   :module: eva.pluginapi

   API method decorator to log API call as INFO
   

.. py:function:: api_log_w(f)
   :module: eva.pluginapi

   API method decorator to log API call as WARNING
   

.. py:function:: api_need_cmd(f)
   :module: eva.pluginapi

   API method decorator to pass if API key has "cmd" allowed
   

.. py:function:: api_need_file_management(f)
   :module: eva.pluginapi

   API method decorator to pass if file management is allowed in server config
   

.. py:function:: api_need_lock(f)
   :module: eva.pluginapi

   API method decorator to pass if API key has "lock" allowed
   

.. py:function:: api_need_master(f)
   :module: eva.pluginapi

   API method decorator to pass if API key is masterkey
   

.. py:function:: api_need_rpvt(f)
   :module: eva.pluginapi

   API method decorator to pass if rpvt is allowed in server config
   

.. py:function:: api_need_sysfunc(f)
   :module: eva.pluginapi

   API method decorator to pass if API key has "sysfunc" allowed
   

.. py:function:: check_product(code)
   :module: eva.pluginapi

   Check controller type
   
   :param code: required controller type (uc, lm or sfa)
   
   :raises RuntimeError: if current controller type is wrong
   

.. py:function:: check_version(min_version)
   :module: eva.pluginapi

   Check plugin API version
   
   :param min_version: min Plugin API version required
   
   :raises RuntimeError: if Plugin API version is too old
   

.. py:function:: clear_thread_local(var, mod=None)
   :module: eva.pluginapi

   Check if thread-local variable exists
   
   :param var: variable name
   :param mod: self module name (optional)
   
   :returns: True if exists
   

.. py:function:: create_db_engine(db_uri, timeout=None)
   :module: eva.pluginapi

   Create SQLAlchemy database Engine
   
   - database timeout is set to core timeout, if not specified
   - database pool size is auto-configured
   - for all engines, except SQLite, "READ UNCOMMITED" isolation level is used
   

.. py:function:: critical()
   :module: eva.pluginapi

   Send critical event
   

.. py:function:: format_db_uri(db_uri)
   :module: eva.pluginapi

   Formats short database URL to SQLAlchemy URI
   
   - if no DB engine specified, SQLite is used
   - if relative SQLite db path is used, it's created under EVA dir
   

.. py:function:: get_aci(field, default=None)
   :module: eva.pluginapi

   get API call info field
   
   :param field: ACI field
   :param default: default value if ACI field isn't set
   
   :returns: None if ACI field isn't set
   

.. py:function:: get_db()
   :module: eva.pluginapi

   get SQLAlchemy connection to primary DB
   

.. py:function:: get_directory(tp)
   :module: eva.pluginapi

   Get path to EVA ICS directory
   
   :param tp: directory type: eva, runtime, ui, pvt or xc
   
   :raises LookupError: if directory type is invalid
   

.. py:function:: get_item(i)
   :module: eva.pluginapi

   Get controller item
   
   :param i: item oid
   
   :returns: None if item is not found
   

.. py:function:: get_logger(mod=None)
   :module: eva.pluginapi

   Get plugin logger
   
   :param mod: self module name (optional)
   
   :returns: logger object
   

.. py:function:: get_masterkey()
   :module: eva.pluginapi

   get master API key
   
   :returns: master API key
   

.. py:function:: get_plugin_db(db, mod=None)
   :module: eva.pluginapi

   Get plugin custom database SQLAlchemy connection
   
   The connection object is stored as thread-local and re-used if possible
   
   :param db: SQLAlchemy DB engine
   

.. py:function:: get_polldelay()
   :module: eva.pluginapi

   Get core poll delay
   

.. py:function:: get_product()
   :module: eva.pluginapi

   Get product object
   
   :returns: namespace(name, code, build)
   

.. py:function:: get_sleep_step()
   :module: eva.pluginapi

   Get core sleep step
   

.. py:function:: get_system_name()
   :module: eva.pluginapi

   Get system name (host name)
   

.. py:function:: get_thread_local(var, default=None, mod=None)
   :module: eva.pluginapi

   Get thread-local variable
   
   :param var: variable name
   :param default: default, if doesn't exists
   :param mod: self module name (optional)
   
   :returns: variable value or None if variable isn't set
   

.. py:function:: get_timeout()
   :module: eva.pluginapi

   Get default timeout
   

.. py:function:: get_userdb()
   :module: eva.pluginapi

   get SQLAlchemy connection to user DB
   

.. py:function:: get_version()
   :module: eva.pluginapi

   Get Plugin API version
   

.. py:function:: has_thread_local(var, mod=None)
   :module: eva.pluginapi

   Check if thread-local variable exists
   
   :param var: variable name
   :param mod: self module name (optional)
   
   :returns: True if exists
   

.. py:function:: key_by_id(key_id)
   :module: eva.pluginapi

   get API key by API key ID
   
   :returns: API key
   

.. py:function:: key_check(*args, ro_op=False, **kwargs)
   :module: eva.pluginapi

   check API key access
   
   Arguments are ACL which can be combined
   
   :param k: API key, required
   :param items: item objects
   :param oid: OID (mqtt-style masks allowed)
   :param allow: check allows
   :param pvt_file: access to pvt resource
   :param pvt_file: access to rpvt resource
   :param ip: caller IP
   :param master: is master access required
   :param sysfunc: is sysfunc required
   :param ro_op: is item operation read-only
   

.. py:function:: key_check_master(*args, ro_op=False, **kwargs)
   :module: eva.pluginapi

   check master API key access
   
   :param k: API key, required
   :param ro_op: is item operation read-only
   

.. py:function:: key_id(k)
   :module: eva.pluginapi

   get key ID by API key
   
   :returns: API key ID
   

.. py:function:: log_traceback()
   :module: eva.pluginapi

   Log traceback
   

.. py:function:: parse_api_params(params, names='', types='', defaults=None)
   :module: eva.pluginapi

   calls parse_function_params but omits API key
   

.. py:function:: parse_function_params(params, names, types='', defaults=None, e=<class 'eva.tools.InvalidParameter'>, ignore_extra=False)
   :module: eva.pluginapi

   :param names: parameter names (list or string if short)
                 S: equal to 'save'
                 Y: equal to 'full'
                 J: equal to '_j'
                 F: equal to 'force'
   :param values: parameter values
                  R: required, any not null and non-empty string
                  r: required, but empty strings are possible
                  s: required, should be string
                  S: required, should be non-empty string
                  b: boolean (or 0/1 or boolean-like strings)
                  B: boolean (or 0/1 or boolean-like strings), required
                  i: integer, can be None
                  f or n: float(number), can be None
                  I: integer, required
                  F or N: float(number), required
                  D: dict, required
                  T: tuple, required
                  X: set, required
                  L: list, required
                  . (dot): optional
                  o: oid, can be null
                  O: OID required
   :param params: dict
   :param defaults: dict (name/value)
   :param e: exception to raise
   

.. py:class:: partial
   :module: eva.pluginapi

   partial(func, *args, **keywords) - new function with partial application
   of the given arguments and keywords.
   
   
   .. py:method:: partial.__call__
      :module: eva.pluginapi
   
      Call self as a function.
      
   
   .. py:method:: partial.__delattr__
      :module: eva.pluginapi
   
      Implement delattr(self, name).
      
   
   .. py:method:: partial.__getattribute__
      :module: eva.pluginapi
   
      Return getattr(self, name).
      
   
   .. py:method:: partial.__new__
      :module: eva.pluginapi
   
      Create and return a new object.  See help(type) for accurate signature.
      
   
   .. py:method:: partial.__reduce__
      :module: eva.pluginapi
   
      Helper for pickle.
      
   
   .. py:method:: partial.__repr__
      :module: eva.pluginapi
   
      Return repr(self).
      
   
   .. py:method:: partial.__setattr__
      :module: eva.pluginapi
   
      Implement setattr(self, name, value).
      
   
   .. py:attribute:: partial.args
      :module: eva.pluginapi
   
      tuple of arguments to future partial calls
   
   .. py:attribute:: partial.func
      :module: eva.pluginapi
   
      function object to use in future partial calls
   
   .. py:attribute:: partial.keywords
      :module: eva.pluginapi
   
      dictionary of keyword arguments to future partial calls

.. py:function:: register_apix(o, sys_api=False, mod=None)
   :module: eva.pluginapi

   Register API extension (APIX) object
   
   All object methods (except internal and private) are automatically exposed
   as API functions
   
   Functions are registered as x_{plugin}_{fn}
   
   :param o: APIX object
   :param sys_api: if True, object functions are registered as SYS API
   :param mod: self module name (optional)
   

.. py:function:: register_lmacro_object(n, o, mod=None)
   :module: eva.pluginapi

   Register custom object for LM PLC macros
   
   Object is registered as x_{plugin}_{n}
   
   :param n: object name
   :param o: object itself
   :param mod: self module name (optional)
   

.. py:function:: register_sfatpl_object(n, o, mod=None)
   :module: eva.pluginapi

   Register custom object for SFA Templates
   
   Object is registered as x_{plugin}_{n}
   
   :param n: object name
   :param o: object itself
   :param mod: self module name (optional)
   

.. py:function:: sendmail(subject=None, text=None, rcp=None)
   :module: eva.pluginapi

   send email message
   
   The function uses config/common/mailer :doc:`registry</registry>` key get
   sender address and list of the recipients (if not specified).
   
   Optional:
       subject: email subject
       text: email text
       rcp: recipient or array of the recipients
   
   :raises FunctionFailed: mail is not sent
   

.. py:function:: set_aci(field, value)
   :module: eva.pluginapi

   set API call info field
   
   :param field: ACI field
   :param value: field value
   
   :returns: True if value is set, False for error (e.g. ACI isn't initialized)
   

.. py:function:: set_thread_local(var, value=None, mod=None)
   :module: eva.pluginapi

   Set thread-local variable
   
   :param var: variable name
   :param value: value to set
   :param mod: self module name (optional)
   

.. py:function:: snmp_get(oid, host, port=161, community='public', timeout=0, retries=0, rf=<class 'str'>, snmp_ver=2, walk=False)
   :module: eva.pluginapi

   :param oid: SNMP OID or MIB name
   :param host: target host
   :param port: target port (default: 161)
   :param community: SNMP community (default: public)
   :param timeout: max SNMP timeout
   :param retries: max retry count (default: 0)
   :param rf: return format: str, float, int or None
   :param snmp_ver: SNMP version (default: 2)
   :param walk: if True, SNMP walk will be performed
   
   :returns: If rf is set to None, raw pysnmp object is returned, otherwise parsed
             to float, int or str
   
             If walk is requested, list of pysnmp objects is returned
   

.. py:function:: snmp_set(oid, value, host, port=161, community='private', timeout=0, retries=0, snmp_ver=2)
   :module: eva.pluginapi

   :param oid: SNMP OID or MIB name
   :param value: value to set
   :param host: target host
   :param port: target port (default: 161)
   :param community: SNMP community (default: public)
   :param timeout: max SNMP timeout
   :param retries: max retry count (default: 0)
   :param snmp_ver: SNMP version (default: 2)
   
   :returns: True if value is set, False if not
   

.. py:function:: spawn(f, *args, **kwargs)
   :module: eva.pluginapi

   Run function as a thread in EVA ICS thread pool
   
   :param f: callable
   :param args/kwargs: passed to function as-is
   
   :returns: concurrent.futures Future object
   

.. py:function:: upnp_discover(st, ip='239.255.255.250', port=1900, mx=True, interface=None, trailing_crlf=True, parse_data=True, discard_headers=['Cache-control', 'Host'], timeout=None)
   :module: eva.pluginapi

   discover uPnP equipment
   
   :param st: service type
   :param ip: multicast ip
   :param port: multicast port
   :param mx: use MX header (=timeout)
   :param interface: network interface (None - scan all)
   :param trailing_crlf: put trailing CRLF at the end of msg
   :param parse_data: if False, raw data will be returned
   :param discard_headers: headers to discard (if parse_data is True)
   :param timeout: socket timeout (for a single interface)
   
   :returns: list of dicts, where IP=equipment IP, otherwise
             dict, where key=equipment IP addr, value=raw ssdp reply. Note: if data
             is parsed, all variables are converted to lowercase and capitalized.
   :rtype: if data is parsed
   
