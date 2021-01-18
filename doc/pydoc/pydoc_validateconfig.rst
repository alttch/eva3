
.. py:class:: GenericX()
   :module: eva.x

   
   .. py:method:: GenericX.validate_config(config={}, config_type='config', ignore_private=False, **kwargs)
      :module: eva.x
   
      Validates module config
      
      Does nothing by default. Can e.g. call self.validate_config_whi to
      validate config with module help info, validate config with JSON schema
      or do everything manually
      
      Note: "driver_assign" always assigns the same parameters for "action"
      and "state" by default. Consider either ignoring config_type='state'
      validation or allow action parameters there.
      
      :param config: config to validate (may be modified on-the-flow to convert
                     variable types for extension config)
      :param config_type: validation config type ('config', 'state', 'action'
                          etc., matches help variable)
      :param ignore_private: allow any private (starting with "_") parameters as
                             they're usually passed as-is to lower level extension (e.g. LPI
                             -> PHI)
      :param kwargs: reserved for the future
      
      :returns: True if config is validated
      
      :raises eva.exceptions.InvalidParameter: if config contains invalid params
      
   
   .. py:method:: GenericX.validate_config_whi(config=None, config_type='config', allow_extra=False, ignore_private=False, xparams=[])
      :module: eva.x
   
      Validate config with module help info
      
      Help info: module help info variable (e.g. __config_help__ for config)
      
      :param config: config to validate
      :param config_type: config type (help var to parse, default is 'config')
      :param allow_extra: allow any extra params in config
      :param xparams: list of allowed extra params
      
      :returns: True if config is validated. Config dict variables are
                automatically parsed and converted to the required types (except
                extra params if not listed)
      
      :raises eva.exceptions.InvalidParameter: if configuration is invalid
      
