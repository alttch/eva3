
.. py:class:: GenericX
   :module: eva.x

   
   .. py:method:: GenericX.validate_config(config={}, config_type='config', **kwargs)
      :module: eva.x
   
      Validates module config
      
      Does nothing by default. Can e.g. call self.validate_config_whi to
      validate config with module help info, validate config with JSON schema
      or do everything manually
      
   
   .. py:method:: GenericX.validate_config_whi(config={}, config_type='config', allow_extra=False, xparams=[])
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
      
