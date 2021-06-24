
.. py:module:: eva.registry


.. py:function:: config_get(key, **kwargs)
   :module: eva.registry

   Get key as configuration object
   

.. py:function:: get_subkeys(key)
   :module: eva.registry

   Get keys recursive as a dict
   

.. py:function:: key_as_dict(key, **kwargs)
   :module: eva.registry

   Work with key as with a dict
   
   with key_as_dict(key): ...
   

.. py:function:: key_decrement(key)
   :module: eva.registry

   Decrement key value
   

.. py:function:: key_delete(key)
   :module: eva.registry

   Delete key
   

.. py:function:: key_delete_field(key, field, **kwargs)
   :module: eva.registry

   Delete key field
   

.. py:function:: key_delete_recursive(key)
   :module: eva.registry

   Delete keys recursive
   

.. py:function:: key_get(key, default=<class 'KeyError'>)
   :module: eva.registry

   Get key
   

.. py:function:: key_get_field(key, field, default=<class 'KeyError'>)
   :module: eva.registry

   Get key field
   

.. py:function:: key_get_recursive(key)
   :module: eva.registry

   Get keys recursive as [(key, value)] list
   

.. py:function:: key_import(key, fh)
   :module: eva.registry

   Import key from stream or file
   

.. py:function:: key_increment(key)
   :module: eva.registry

   Increment key value
   

.. py:function:: key_set(key, value, **kwargs)
   :module: eva.registry

   Set key
   

.. py:function:: key_set_field(key, field, value, **kwargs)
   :module: eva.registry

   Set key field
   

.. py:function:: safe_purge()
   :module: eva.registry

   Purge database, keep broken keys
   
