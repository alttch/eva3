
.. py:module:: eva.uc.driverapi


.. py:function:: critical()
   :module: eva.uc.driverapi

   Ask the core to raise critical exception
   

.. py:function:: get_driver(driver_id)
   :module: eva.uc.driverapi

   Get driver module by id
   

.. py:function:: get_phi(phi_id)
   :module: eva.uc.driverapi

   Get PHI module by id
   

.. py:function:: get_polldelay()
   :module: eva.uc.driverapi

   Get UC poll delay
   

.. py:function:: get_sleep_step()
   :module: eva.uc.driverapi

   Get the default sleep step
   

.. py:function:: get_system_name()
   :module: eva.uc.driverapi

   Get EVA ICS node name
   

.. py:function:: get_timeout()
   :module: eva.uc.driverapi

   Get the default core timeout
   

.. py:function:: get_version()
   :module: eva.uc.driverapi

   Get DriverAPI version
   

.. py:function:: handle_phi_event(phi, port=None, data=None)
   :module: eva.uc.driverapi

   Ask the core to handle PHI event
   
   :param phi: PHI module the event is from (usually =self)
   :param port: the port, where the event is happened
   :param data: { port: value } dict with the maximum of state ports available
                which may be changed because of the event
   

.. py:function:: lock(l, timeout=None, expires=None)
   :module: eva.uc.driverapi

   Acquire a core lock
   
   :param l: lock ID/name
   :param timeout: timeout to acquire the lock
   :param expires: lock auto-expiration time
   

.. py:function:: log_traceback()
   :module: eva.uc.driverapi

   Ask the core to log traceback of the latest error
   

.. py:function:: lpi_constructor(f)
   :module: eva.uc.driverapi

   LPI constructor decorator
   
   Automatically calls parent construction, handles "info_only" module loads
   

.. py:function:: phi_constructor(f)
   :module: eva.uc.driverapi

   PHI constructor decorator
   
   Automatically calls parent construction, handles "info_only" module loads
   

.. py:function:: transform_value(value, multiply=None, divide=None, round_to=None)
   :module: eva.uc.driverapi

   Generic value transformer
   
   :param multiply: multiply the value on
   :param divide: divide the value on
   :param round_to: round the value to X digits after comma
   

.. py:function:: unlock(l)
   :module: eva.uc.driverapi

   Release a core lock
   
   :param l: lock ID/name
   
